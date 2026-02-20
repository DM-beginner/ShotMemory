import contextlib
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter

from core.base_code import APIStatus
from core.base_schema import BaseResponse
from core.custom_exception import BusinessError
from core.database import SessionDep
from core.storage import StorageDep
from core.unify_response import UnifyResponse
from services.auth.routers.user_deps import CurrentUser
from services.photo_story.models.photo_model import Photo
from services.photo_story.repos.photo_repo import PhotoRepo
from services.photo_story.schemas.photo_schema import (
    PhotoCreateRequest,
    PhotoListResponse,
    PhotoResponse,
    PhotoUpdateRequest,
)

router = APIRouter(tags=["photo"], prefix="/photo")


@router.post("", response_model=BaseResponse[PhotoResponse])
async def create_photo(
    request: PhotoCreateRequest,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    创建照片记录

    - 需要登录认证
    - 用于在上传文件后创建照片元数据记录
    - 支持 EXIF 数据、地理位置等信息
    """
    # 构建 PostGIS POINT 格式（如果提供了经纬度）
    location_wkt = None
    if request.latitude is not None and request.longitude is not None:
        location_wkt = f"SRID=4326;POINT({request.longitude} {request.latitude})"

    # 创建照片记录
    photo = Photo(
        user_id=current_user.id,
        object_key=request.object_key,
        width=request.width,
        height=request.height,
        location=location_wkt,
        exif_data=request.exif_data,
        taken_at=request.taken_at or datetime.now(),
    )

    photo = await PhotoRepo.create(db, photo)

    return UnifyResponse.success(
        data=PhotoResponse.model_validate(photo).model_dump(),
        message="照片记录创建成功",
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
        raise BusinessError(
            code=APIStatus.NOT_FOUND.code,
            message="照片不存在",
            status_code=404,
        )

    # 权限校验：只能查看自己的照片
    if photo.user_id != current_user.id:
        raise BusinessError(
            code=APIStatus.FORBIDDEN.code,
            message="无权访问此照片",
            status_code=403,
        )

    return UnifyResponse.success(
        data=PhotoResponse.model_validate(photo).model_dump(),
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
            items=[item.model_dump() for item in items],
        ).model_dump(),
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
        raise BusinessError(
            code=APIStatus.NOT_FOUND.code,
            message="照片不存在",
            status_code=404,
        )

    # 权限校验
    if photo.user_id != current_user.id:
        raise BusinessError(
            code=APIStatus.FORBIDDEN.code,
            message="无权修改此照片",
            status_code=403,
        )

    # 更新字段
    if request.exif_data is not None:
        photo.exif_data = request.exif_data

    photo = await PhotoRepo.update(db, photo)

    return UnifyResponse.success(
        data=PhotoResponse.model_validate(photo).model_dump(),
        message="照片信息更新成功",
    )


@router.delete("/{photo_id}", response_model=BaseResponse[dict])
async def delete_photo(
    photo_id: UUID,
    db: SessionDep,
    storage: StorageDep,
    current_user: CurrentUser,
):
    """
    删除照片

    - 需要登录认证
    - 只能删除自己的照片
    - 会同时删除数据库记录和 OSS 文件
    """
    photo = await PhotoRepo.get_by_id(db, photo_id)

    if not photo:
        raise BusinessError(
            code=APIStatus.NOT_FOUND.code,
            message="照片不存在",
            status_code=404,
        )

    # 权限校验
    if photo.user_id != current_user.id:
        raise BusinessError(
            code=APIStatus.FORBIDDEN.code,
            message="无权删除此照片",
            status_code=403,
        )

    # 删除数据库记录
    success = await PhotoRepo.delete(db, photo_id)

    if not success:
        raise BusinessError(
            code=APIStatus.SYSTEM_ERROR.code,
            message="删除照片失败",
            status_code=500,
        )

    # 删除 OSS 文件（异步，失败不影响主流程）
    with contextlib.suppress(Exception):
        await storage.delete_file(photo.object_key)

    return UnifyResponse.success(
        data={"deleted": True},
        message="照片删除成功",
    )
