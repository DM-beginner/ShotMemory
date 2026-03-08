"""
photo_story 服务专属业务异常类。
"""

from core.exceptions import APIStatus, BaseError

# ---------------------------------------------------------------------------
# 领域异常：Worker / 图片处理内部使用，不对外暴露为 HTTP 响应
# ---------------------------------------------------------------------------


class PhotoProcessingError(BaseError):
    """Worker 处理照片任务的领域异常基类。"""

    def __init__(
        self,
        code: int = APIStatus.PHOTO_PROCESSING_FAILED.code,
        message: str = APIStatus.PHOTO_PROCESSING_FAILED.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=500)


class ExifExtractionError(BaseError):
    """EXIF 元数据提取失败异常。"""

    def __init__(
        self,
        code: int = APIStatus.PHOTO_PROCESSING_FAILED.code,
        message: str = APIStatus.PHOTO_PROCESSING_FAILED.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=404)


class ThumbnailGenerationError(BaseError):
    """缩略图生成失败异常。"""

    def __init__(
        self,
        code: int = APIStatus.THUMBNAIL_GENERATION_FAILED.code,
        message: str = APIStatus.THUMBNAIL_GENERATION_FAILED.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=500)
