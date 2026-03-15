import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from loguru import logger

from core.storage.interface import StorageStrategy, UploadResult


class LocalStorageStrategy(StorageStrategy):
    """
    本地文件存储策略（开发环境使用）
    - 原图保存到 uploads/originals/ 目录
    - 缩略图保存到 uploads/thumbnails/ 目录
    - 返回可通过 StaticFiles 访问的 URL
    """

    def __init__(self, upload_dir: str, base_url: str) -> None:
        """
        Args:
            upload_dir: 本地保存根目录（如 "uploads"）
            base_url: 静态文件访问的基础 URL（如 "http://localhost:5683/static"）
        """
        self.upload_dir = Path(upload_dir)
        self.base_url = base_url.rstrip("/")

        # 预创建原图和缩略图子目录
        self.originals_dir = self.upload_dir / "originals"
        self.thumbnails_dir = self.upload_dir / "thumbnails"
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file: UploadFile) -> UploadResult:
        """
        将原图保存到 originals/ 子目录
        """
        original_name = file.filename or "unknown"
        suffix = Path(original_name).suffix
        unique_name = f"{uuid.uuid4().hex}{suffix}"

        file_path = self.originals_dir / unique_name
        content = await file.read()

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        object_key = f"{self.upload_dir}/originals/{unique_name}"

        logger.info(f"原图已保存到本地: {file_path}")

        return UploadResult(object_key=object_key)

    async def upload_bytes(
        self,
        data: bytes,
        suffix: str,
        subdir: str = "thumbnails",
        stem: str | None = None,
    ) -> UploadResult:
        """
        将字节流保存到指定子目录（如 thumbnails/、videos/）
        """
        target_dir = self.upload_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        unique_name = f"{stem}{suffix}" if stem else f"{uuid.uuid4().hex}{suffix}"
        file_path = target_dir / unique_name

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)

        object_key = f"{self.upload_dir}/{subdir}/{unique_name}"

        logger.info(f"文件已保存到本地: {file_path}")

        return UploadResult(object_key=object_key)

    async def delete_file(self, file_url: str) -> bool:
        """
        删除本地文件

        从 URL 中剥离 base_url 前缀，还原完整相对路径后定位并删除文件。
        兼容 originals/ 和 thumbnails/ 子目录结构。
        """
        try:
            # 剥离 base_url 前缀，还原真实相对路径
            # 例: "http://localhost:5683/static/uploads/originals/xxx.jpg"
            #  → "uploads/originals/xxx.jpg"
            file_path = Path(file_url)

            if file_path.exists():
                file_path.unlink()
                logger.info(f"文件已删除: {file_path}")
                return True

            logger.warning(f"文件不存在，无法删除: {file_path}")
            return False

        except Exception:
            logger.exception(f"删除文件失败: {file_url}")
            return False
