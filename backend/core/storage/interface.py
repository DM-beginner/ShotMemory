from abc import ABC, abstractmethod

from fastapi import UploadFile


class StorageStrategy(ABC):
    """
    存储策略抽象基类
    - 定义文件上传/删除的标准接口
    - 具体实现类（本地存储、阿里云 OSS 等）必须实现所有抽象方法
    """

    @abstractmethod
    async def upload_file(self, file: UploadFile) -> str:
        """
        上传文件

        Args:
            file: FastAPI 的 UploadFile 对象

        Returns:
            文件的访问 URL
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
