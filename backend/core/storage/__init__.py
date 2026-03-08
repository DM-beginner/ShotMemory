from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from core.config import settings
from core.storage.aliyun import AliyunOSSStrategy
from core.storage.interface import StorageStrategy, UploadResult
from core.storage.local import LocalStorageStrategy

__all__ = [
    "AliyunOSSStrategy",
    "LocalStorageStrategy",
    "StorageDep",
    "StorageStrategy",
    "UploadResult",
    "get_storage_service",
]


@lru_cache(maxsize=1)
def get_storage_service() -> StorageStrategy:
    """
    根据环境变量返回对应的存储策略实例

    - dev  -> LocalStorageStrategy（本地文件存储）
    - prod -> AliyunOSSStrategy（阿里云 OSS）

    使用 lru_cache 保证全局单例，避免重复创建
    """
    if settings.ENV == "prod":
        return AliyunOSSStrategy(
            access_key_id=settings.OSS_ACCESS_KEY_ID,
            access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
            bucket_name=settings.OSS_BUCKET_NAME,
            endpoint=settings.OSS_ENDPOINT,
            cdn_domain=settings.OSS_CDN_DOMAIN,
        )

    # 开发环境：本地存储
    base_url = f"http://{settings.HOST}:{settings.PORT}{settings.STATIC_URL_PREFIX}"
    return LocalStorageStrategy(
        upload_dir=settings.UPLOAD_DIR,
        base_url=base_url,
    )


# 类型别名，与 SessionDep / CurrentUser 风格一致
StorageDep = Annotated[StorageStrategy, Depends(get_storage_service)]
