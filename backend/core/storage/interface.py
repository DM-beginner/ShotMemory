from abc import ABC, abstractmethod

from fastapi import UploadFile
from pydantic import BaseModel


class UploadResult(BaseModel):
    """文件上传结果"""

    thumbnail_key: str  # 缩略图相对路径
    object_key: str  # 相对路径（用于数据库存储）


class StorageStrategy(ABC):
    """
    存储策略抽象基类
    - 定义文件上传/删除的标准接口
    - 具体实现类（本地存储、阿里云 OSS 等）必须实现所有抽象方法
    """

    @abstractmethod
    async def upload_file(self, file: UploadFile) -> UploadResult:
        """
        上传文件

        Args:
            file: FastAPI 的 UploadFile 对象

        Returns:
            UploadResult 对象，包含访问 URL 和 object_key
        """
        ...

    @abstractmethod
    async def upload_bytes(self, data: bytes, suffix: str) -> UploadResult:
        """
        直接上传字节流（用于程序生成的文件，如缩略图）

        Args:
            data: 文件字节内容
            suffix: 文件扩展名（如 ".webp"），用于生成文件名

        Returns:
            UploadResult 对象，包含访问 URL 和 object_key
        """
        ...

    @abstractmethod
    async def delete_file(self, file_url: str) -> bool:
        """
        删除文件

        Args:
            file_url: 文件的访问 URL

        Returns:
            是否删除成功
        """
        ...
