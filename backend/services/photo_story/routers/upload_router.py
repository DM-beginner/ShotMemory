from fastapi import APIRouter, UploadFile

from core.base_code import APIStatus
from core.base_schema import BaseResponse
from core.custom_exception import BusinessError
from core.storage import StorageDep
from core.unify_response import UnifyResponse
from services.auth.routers.user_deps import CurrentUser
from services.photo_story.schemas.photo_schema import UploadResponseData

router = APIRouter(tags=["photo"], prefix="/photo")

# 允许上传的图片类型
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}

# 最大文件大小（50MB）
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload", response_model=BaseResponse[UploadResponseData])
async def upload_photo(
    file: UploadFile,
    storage: StorageDep,
    _current_user: CurrentUser,  # 依赖注入式认证，在任何需要认证的接口中只需要加上 current_user: CurrentUser 参数即可自动获得认证保护。
):
    """
    上传照片

    - 需要登录认证
    - 支持 JPEG / PNG / GIF / WebP / SVG 格式
    - 文件大小限制 50MB
    - 存储策略根据环境自动切换（本地 / 阿里云 OSS）
    """
    # 1. 校验文件类型
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise BusinessError(
            code=APIStatus.FILE_TYPE_NOT_ALLOWED.code,
            message=f"{APIStatus.FILE_TYPE_NOT_ALLOWED.msg}，仅支持 JPEG/PNG/GIF/WebP/SVG",
            status_code=400,
        )

    # 2. 校验文件大小
    if file.size and file.size > MAX_FILE_SIZE:
        raise BusinessError(
            code=APIStatus.FILE_TOO_LARGE.code,
            message=f"{APIStatus.FILE_TOO_LARGE.msg}，最大 50MB",
            status_code=400,
        )

    # 3. 调用存储策略上传（解耦：不关心具体是本地还是 OSS）
    try:
        url = await storage.upload_file(file)
    except Exception as e:
        raise BusinessError(
            code=APIStatus.FILE_UPLOAD_FAILED.code,
            message=APIStatus.FILE_UPLOAD_FAILED.msg,
            status_code=500,
        ) from e

    # 4. 返回上传结果
    response_data = UploadResponseData(
        url=url,
        filename=file.filename or "unknown",
    )
    return UnifyResponse.success(
        data=response_data.model_dump(),
        message="上传成功",
    )
