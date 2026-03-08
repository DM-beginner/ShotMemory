import contextlib
from typing import Any, Final
from uuid import UUID

from fastapi import APIRouter, Body, UploadFile
from loguru import logger

from core.base_schema import BaseResponse
from core.database import RedisDep, SessionDep
from core.exceptions import APIStatus, BaseError
from core.storage import StorageDep
from core.unify_response import UnifyResponse
from services.auth.routers.user_deps import CurrentUser
from services.photo_story.repos.photo_repo import PhotoRepo
from services.photo_story.schemas.photo_schema import (
    PhotoListResponse,
    PhotoResponse,
    PhotoUpdateRequest,
)

router = APIRouter(tags=["photo"], prefix="/photo")

# 允许上传的图片类型 → 对应临时文件后缀（供 ExifTool 识别格式）
ALLOWED_CONTENT_TYPES: Final[dict[str, str]] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",  # Apple iOS 默认格式
    "image/heif": ".heif",  # 高效图像文件通用格式
    "image/avif": ".avif",  # 现代高压缩比 Web 格式
}

# 最大文件大小（50MB）
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_FILES_PER_BATCH = 50


@router.post("/uploads", response_model=BaseResponse[list[PhotoResponse]])
async def upload_photos(
    files: list[UploadFile],
    storage: StorageDep,
    db: SessionDep,
    arq_redis: RedisDep,
    current_user: CurrentUser,
):
    """
    批量上传照片并创建数据库记录

    - 支持多图上传（单次最多 50 张）
    - 采用 All-or-Nothing 校验策略（只要有一张不合法，直接拒绝全部）
    - 具备失败回滚机制（清理中途上传到 OSS 的孤儿文件）
    """
    # 防御性限制
    if not files:
        raise BaseError(
            code=APIStatus.BAD_REQUEST.code,
            message="上传文件列表不能为空",
            status_code=400,
        )

    if len(files) > MAX_FILES_PER_BATCH:
        raise BaseError(
            code=APIStatus.BAD_REQUEST.code,
            message=f"单次最多允许上传 {MAX_FILES_PER_BATCH} 张照片",
            status_code=400,
        )

    # 1. 严格的前置校验 (Fail-Fast 策略)
    # 在真正消耗带宽上传前，检查所有文件。防止传到一半才报错。
    for file in files:
        # 1. 校验文件类型
        content_type = file.content_type or ""
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise BaseError(
                code=APIStatus.FILE_TYPE_NOT_ALLOWED.code,
                message=f"{APIStatus.FILE_TYPE_NOT_ALLOWED.msg}，仅支持 {', '.join(ALLOWED_CONTENT_TYPES.keys())}",
                status_code=400,
            )
        # 2. 校验文件大小
        if file.size and file.size > MAX_FILE_SIZE:
            raise BaseError(
                code=APIStatus.FILE_TOO_LARGE.code,
                message=f"文件 {file.filename} 超过最大限制 50MB",
                status_code=400,
            )

    photo_dicts: list[dict[str, Any]] = []
    uploaded_urls: list[str] = []  # 用于记录已上传的路径，方便灾难回滚

    try:
        # 2. 开始逐一处理
        for file in files:
            # A. 上传存储
            upload_result = await storage.upload_file(file)
            uploaded_urls.append(upload_result.url)

            # B. 构建并写入记录
            # 注: 如果 PhotoRepo 支持 create_many(db, photos) 会更高效
            # 这里为了不打破你原有的 Repo 结构，沿用单次 create
            # 组装扁平化字典，为 Core 批量插入做准备
            photo_dicts.append(
                {
                    "user_id": current_user.id,
                    "object_key": upload_result.object_key,
                    "thumbnail_key": None,
                    "width": None,
                    "height": None,
                    "location_wkt": None,
                    "exif_data": None,
                    "taken_at": None,
                }
            )
            photos = await PhotoRepo.create_many(db, photo_dicts)

            # C. 投递后台任务
            for photo in photos:
                await arq_redis.enqueue_job(
                    "parse_photo_exif",
                    str(photo.id),
                    photo.object_key,
                )
    except Exception as e:
        # 5. 灾难回滚 (Rollback)
        logger.error(f"批量上传发生异常，开始回滚 {len(uploaded_urls)} 个已上传文件")
        for url in uploaded_urls:
            with contextlib.suppress(Exception):
                await storage.delete_file(url)

        raise BaseError(
            code=APIStatus.SYSTEM_ERROR.code,
            message="批量上传或入库失败，已自动回滚",
            status_code=500,
        ) from e

    # 6. 组装响应
    return UnifyResponse.success(
        data=[PhotoResponse.model_validate(p).model_dump(mode="json") for p in photos],
        message=f"成功上传 {len(photos)} 张照片，EXIF 数据处理中",
    )


@router.get("/{photo_id}", response_model=BaseResponse[PhotoResponse])
async def get_photo(
    photo_id: UUID,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    获取单张照片详情

    - 需要登录认证
    - 只能查看自己的照片
    """
    photo = await PhotoRepo.get_by_id(db, photo_id)

    if not photo:
        raise BaseError(
            code=APIStatus.NOT_FOUND.code,
            message="照片不存在",
            status_code=404,
        )

    # 权限校验：只能查看自己的照片
    if photo.user_id != current_user.id:
        raise BaseError(
            code=APIStatus.FORBIDDEN.code,
            message="无权访问此照片",
            status_code=403,
        )

    return UnifyResponse.success(
        data=PhotoResponse.model_validate(photo).model_dump(mode="json"),
    )


@router.get("", response_model=BaseResponse[PhotoListResponse])
async def get_my_photos(
    db: SessionDep,
    current_user: CurrentUser,
    limit: int = 20,
    offset: int = 0,
):
    """
    获取当前用户的照片列表

    - 需要登录认证
    - 支持分页
    - 按拍摄时间倒序排列
    """
    photos = await PhotoRepo.get_by_user_id(db, current_user.id, limit, offset)

    # 转换为响应格式
    items = [PhotoResponse.model_validate(photo) for photo in photos]

    # 注意：这里暂不实现 total 统计（需要额外查询），前端可根据返回数量判断是否还有更多
    return UnifyResponse.success(
        data=PhotoListResponse(
            total=len(items),  # 简化实现：返回当前页数量
            items=items,
        ).model_dump(mode="json"),
    )


@router.patch("/{photo_id}", response_model=BaseResponse[PhotoResponse])
async def update_photo(
    photo_id: UUID,
    request: PhotoUpdateRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    更新照片信息

    - 需要登录认证
    - 只能更新自己的照片
    - 目前支持更新 EXIF 数据
    """
    photo = await PhotoRepo.get_by_id(db, photo_id)

    if not photo:
        raise BaseError(
            code=APIStatus.NOT_FOUND.code,
            message="照片不存在",
            status_code=404,
        )

    # 权限校验
    if photo.user_id != current_user.id:
        raise BaseError(
            code=APIStatus.FORBIDDEN.code,
            message="无权修改此照片",
            status_code=403,
        )

    # 更新字段
    if request.exif_data is not None:
        photo.exif_data = request.exif_data

    photo = await PhotoRepo.update(db, photo)

    return UnifyResponse.success(
        data=PhotoResponse.model_validate(photo).model_dump(mode="json"),
        message="照片信息更新成功",
    )


@router.delete("/{photo_id}", response_model=BaseResponse[dict])
async def delete_photo(
    photo_id: UUID,
    db: SessionDep,
    arq_redis: RedisDep,
    current_user: CurrentUser,
):
    """
    删除照片

    - 需要登录认证
    - 只能删除自己的照片
    - 会同时删除数据库记录和 OSS 文件
    """
    # 1. 提取 OSS keys 并在底层完成越权拦截 (复用批量接口的高效方法)
    # 只要查不到，要么是不存在，要么是被别人锁了，统一返回 404 防止黑客枚举攻击
    keys_to_delete = await PhotoRepo.get_keys_for_deletion(
        db, [photo_id], current_user.id
    )

    if not keys_to_delete:
        raise BaseError(
            code=APIStatus.NOT_FOUND.code,
            message="照片不存在或无权删除",
            status_code=404,
        )

    # 2. 原生 SQL 直接物理删除
    await PhotoRepo.delete_many(db, [photo_id], current_user.id)

    # 3. 提取 keys 扔给后台 arq 队列清理
    oss_keys: list[str] = []
    obj_key, thumb_key = keys_to_delete[0]
    oss_keys.append(obj_key)
    if thumb_key:
        oss_keys.append(thumb_key)

    if oss_keys:
        await arq_redis.enqueue_job("delete_oss_files", oss_keys)

    return UnifyResponse.success(message="照片删除成功")


@router.post("/batch-delete", response_model=BaseResponse[dict])
async def batch_delete_photos(
    photo_ids: list[UUID] = Body(
        ..., max_length=50, description="要删除的照片ID列表，单次最多50张"
    ),
    db: SessionDep = None,
    arq_redis: RedisDep = None,  # 注入 arq_redis 队列客户端
    current_user: CurrentUser = None,
):
    """
    批量删除照片

    - 需要登录认证
    - 极速短事务：在数据库层利用 IN 语句一次性删除
    - 异步清理：将 OSS 文件 keys 投递给 arq 队列，保证绝对清理且具备重试机制
    """
    if not photo_ids:
        return UnifyResponse.success(message="没有需要删除的照片")

    # 1. 提取要删除的 OSS keys (必须在 DB 删除前执行)
    keys_to_delete = await PhotoRepo.get_keys_for_deletion(
        db, photo_ids, current_user.id
    )

    if not keys_to_delete:
        return UnifyResponse.success(message="未找到符合条件的照片，或已删除")

    # 2. 原生 SQL 批量删除数据库记录
    deleted_count = await PhotoRepo.delete_many(db, photo_ids, current_user.id)

    # 3. 提取所有需要物理删除的 keys
    oss_keys: list[str] = []
    for obj_key, thumb_key in keys_to_delete:
        oss_keys.append(obj_key)
        if thumb_key:
            oss_keys.append(thumb_key)

    # 4. 投递到 arq 后台队列 (取代原来的 asyncio.create_task)
    if oss_keys:
        await arq_redis.enqueue_job("delete_oss_files", oss_keys)

    return UnifyResponse.success(message=f"成功删除 {deleted_count} 张照片")
