import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from loguru import logger

from core.storage.interface import StorageStrategy


class LocalStorageStrategy(StorageStrategy):
    """
    本地文件存储策略（开发环境使用）
    - 将文件保存到本地 uploads/ 目录
    - 返回可通过 StaticFiles 访问的 URL
    """

    def __init__(self, upload_dir: str, base_url: str) -> None:
        """
        Args:
            upload_dir: 本地保存目录（如 "uploads"）
            base_url: 静态文件访问的基础 URL（如 "http://localhost:5683/static"）
        """
        self.upload_dir = Path(upload_dir)
        self.base_url = base_url.rstrip("/")

        # 确保上传目录存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file: UploadFile) -> str:
        """
        将文件保存到本地目录

        流程：
        1. 生成 UUID 文件名（防止冲突）
        2. 使用 aiofiles 异步写入
        3. 返回静态访问 URL
        """
        # 提取文件扩展名
        original_name = file.filename or "unknown"
        suffix = Path(original_name).suffix  # 如 .jpg, .png
        unique_name = f"{uuid.uuid4().hex}{suffix}"

        # 写入文件
        file_path = self.upload_dir / unique_name
        content = await file.read()

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        url = f"{self.base_url}/{self.upload_dir}/{unique_name}"
        logger.info(f"文件已保存到本地: {file_path} -> {url}")

        return url

    async def delete_file(self, file_url: str) -> bool:
        """
        删除本地文件

        从 URL 中解析文件名，定位到本地路径并删除
        """
        try:
            # URL 格式: http://localhost:5683/static/uploads/xxx.jpg
            # 提取最后一段作为文件名
            # Path 类在内部定义了 __truediv__ 方法。当你使用 / 时，它不代表数学除法，而是路径拼接。
            filename = file_url.rsplit("/", maxsplit=1)[-1]
            file_path = self.upload_dir / filename

            if file_path.exists():
                # 删除一个路径指向的文件或符号链接。（文件夹需要用 rmdir()）。

                file_path.unlink()
                logger.info(f"文件已删除: {file_path}")
                return True

            logger.warning(f"文件不存在，无法删除: {file_path}")
            return False

        except Exception:
            logger.exception(f"删除文件失败: {file_url}")
            return False
