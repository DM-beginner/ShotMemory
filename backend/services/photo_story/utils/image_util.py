import asyncio
import contextlib
import mmap
import re
import subprocess
import tempfile
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Any

from exiftool import ExifToolHelper
from loguru import logger
from PIL import Image, ImageOps

from services.photo_story.exceptions import ThumbnailGenerationError
from services.photo_story.schemas.photo_schema import ImageMetadata

# ---------------------------------------------------------------------------
# Pillow 安全限制：收紧像素上限
# 默认 89.5M 像素过高，生成 400px 缩略图不需要那么大的解压缓冲区。
# 50M 像素 ≈ 7000×7000，覆盖所有合理相机照片，单张峰值 ~200MB（RGBA）。
# ---------------------------------------------------------------------------
Image.MAX_IMAGE_PIXELS = 50_000_000

# 排除的二进制大字段（base64 编码的缩略图/预览图，单个可达几十 KB）
_BINARY_KEYS: frozenset[str] = frozenset(
    {
        "ThumbnailImage",
        "PreviewImage",
        "JpgFromRaw",
        "OtherImage",
        "MPImage1",
        "MPImage2",
        "PreviewTIFF",
        "PreviewIPTC",
    }
)

# 命名空间优先级：索引越小优先级越高
# EXIF 优先（相机原始数据），Composite 提供已转换的 GPS 十进制值
# XMP/IPTC 可能含后期编辑值，优先级靠后（已进行倒序）
_NS_PRIORITY: tuple[str, ...] = (
    "ExifTool",
    "File",
    "IPTC",
    "XMP",
    "MakerNotes",
    "Composite",
    "EXIF",
)
_PRIORITY_SET: frozenset[str] = frozenset(_NS_PRIORITY)

# Android 动态照片：纯 Python 快路径用的预编译正则和 ftyp 特征码
_MICRO_VIDEO_OFFSET_RE = re.compile(b'MicroVideoOffset="(\\d+)"')
_MOTION_PHOTO_OFFSET_RE = re.compile(b'MotionPhotoOffset[>"]\\s*(\\d+)')
_FTYP_SIGNATURES: tuple[bytes, ...] = (
    b"ftypisom",
    b"ftypmp42",
    b"ftypMSNV",
    b"ftyp3gp5",
)


class ImageUtil:
    """图片元数据工具类，基于 pyexiftool 解析 EXIF 数据"""

    # ==================================================================
    # 公开异步入口 — 基于路径（核心，零内存中转）
    # ==================================================================

    @classmethod
    async def extract_metadata_from_path(cls, path: Path) -> ImageMetadata:
        """异步入口：exiftool 直接读文件路径，无需内存中转。"""
        return await asyncio.to_thread(cls._extract_from_file, path)

    @classmethod
    async def generate_thumbnail_from_path(
        cls, path: Path, max_side: int = 400
    ) -> bytes:
        """异步入口：Pillow 直接从文件路径读取，按需加载磁盘页面。"""
        return await asyncio.to_thread(cls._thumbnail_from_file, path, max_side)

    @classmethod
    async def prepare_video_from_path(
        cls, input_path: Path, input_suffix: str
    ) -> bytes | None:
        """异步入口：ffmpeg 直接读文件路径，不写输入临时文件。"""
        return await asyncio.to_thread(
            cls._prepare_video_from_file, input_path, input_suffix
        )

    @classmethod
    async def extract_embedded_video_from_path(
        cls, path: Path, suffix: str
    ) -> bytes | None:
        """异步入口：mmap 内存映射提取嵌入视频，OS 按需加载页面。"""
        return await asyncio.to_thread(cls._extract_video_from_file, path, suffix)

    # ==================================================================
    # 公开异步入口 — 基于字节（向后兼容包装）
    # ==================================================================

    @classmethod
    async def extract_metadata(
        cls, image_buffer: bytes, suffix: str = ".jpg"
    ) -> ImageMetadata:
        """异步入口：字节版（兼容），内部写临时文件后调用路径版。"""
        return await asyncio.to_thread(cls._extract_sync, image_buffer, suffix)

    @classmethod
    async def generate_thumbnail(cls, buffer: bytes, max_side: int = 400) -> bytes:
        """异步入口：字节版（兼容），内部写临时文件后调用路径版。"""
        return await asyncio.to_thread(cls._thumbnail_sync, buffer, max_side)

    @classmethod
    async def extract_embedded_video(
        cls, image_buffer: bytes, suffix: str = ".jpg"
    ) -> bytes | None:
        """异步入口：字节版（兼容），内部写临时文件后调用路径版。"""
        return await asyncio.to_thread(cls._extract_video_sync, image_buffer, suffix)

    @classmethod
    async def extract_content_identifier(
        cls, file_bytes: bytes, suffix: str
    ) -> str | None:
        """异步入口：提取 Apple Live Photo 的 ContentIdentifier UUID。"""
        return await asyncio.to_thread(
            cls._extract_content_identifier_sync, file_bytes, suffix
        )

    @classmethod
    async def prepare_video_for_web(
        cls,
        video_bytes: bytes,
        input_suffix: str,
    ) -> bytes | None:
        """异步入口：字节版（兼容），内部写临时文件后调用路径版。"""
        return await asyncio.to_thread(
            cls._prepare_video_sync, video_bytes, input_suffix
        )

    # ==================================================================
    # 同步核心 — 基于路径（核心实现）
    # ==================================================================

    @classmethod
    def _extract_from_file(cls, path: Path) -> ImageMetadata:
        """核心：exiftool 直接读文件路径，无临时文件开销。"""
        try:
            raw_exif = cls._call_exiftool(path)
            filtered = cls._filter_binary(raw_exif)
            flat = cls._flatten_by_priority(filtered)
            return ImageMetadata.model_validate(flat)
        except Exception:
            logger.exception("EXIF 提取过程发生致命崩溃，执行极其安全的全局兜底")
            return ImageMetadata()

    @classmethod
    def _thumbnail_from_file(cls, path: Path, max_side: int = 400) -> bytes:
        """核心：Pillow 从文件路径读取，按需加载磁盘页面，避免全量内存拷贝。"""
        try:
            with Image.open(path) as img:
                img.load()

                img = ImageOps.exif_transpose(img)
                img = (
                    img.convert("RGBA")
                    if img.mode in ("RGBA", "P")
                    else img.convert("RGB")
                )
                img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

                with BytesIO() as out:
                    img.save(out, format="WEBP", quality=60, method=6)
                    return out.getvalue()

        except Image.DecompressionBombError as e:
            logger.error(f"遭遇图片解压炸弹，拒绝处理: {e!s}")
            raise ThumbnailGenerationError(message="图片分辨率过大，拒绝处理") from e
        except Exception as e:
            logger.exception("Pillow 生成缩略图发生不可恢复异常")
            raise ThumbnailGenerationError(message=f"缩略图生成失败: {e!s}") from e

    @classmethod
    def _prepare_video_from_file(
        cls, input_path: Path, _input_suffix: str = ""
    ) -> bytes | None:
        """核心：ffmpeg 直接读输入文件路径，只创建输出临时文件。"""
        output_path = Path(tempfile.mktemp(suffix="_web.mp4", dir=input_path.parent))
        try:
            transcode = cls._needs_transcode(input_path)

            if transcode:
                logger.debug("视频需要转码 (非 H.264)")
                cmd = [
                    "ffmpeg",
                    "-i",
                    str(input_path),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    "-y",
                    str(output_path),
                ]
            else:
                logger.debug("视频仅 remux (H.264)")
                cmd = [
                    "ffmpeg",
                    "-i",
                    str(input_path),
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    "-y",
                    str(output_path),
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.error(
                    f"ffmpeg 失败 (code={result.returncode}): "
                    f"{result.stderr.decode(errors='replace')[-1000:]}"
                )
                return None

            return output_path.read_bytes()
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg 转码超时 (120s)")
            return None
        except Exception:
            logger.exception("视频处理失败")
            return None
        finally:
            with contextlib.suppress(OSError):
                output_path.unlink()

    @classmethod
    def _extract_video_from_file(cls, path: Path, _suffix: str = "") -> bytes | None:
        """
        mmap 版嵌入视频提取：
        - OS 按需加载页面到物理内存，而非 read() 全部内容
        - 找到视频偏移后，只切片拷贝视频部分（通常 2-5MB）
        - 快路径（mmap 搜索）失败时，降级到 exiftool 直接读文件路径
        """
        file_size = path.stat().st_size
        if file_size < 1000:
            return None

        # 快路径：mmap 内存映射搜索
        try:
            with (
                open(path, "rb") as f,
                mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm,
            ):
                result = cls._fast_extract_mp4_from_mmap(mm, file_size)
                if result:
                    logger.debug("视频提取：mmap 快路径命中")
                    return result
        except Exception:
            logger.debug("视频提取：mmap 快路径异常，降级 exiftool")

        # 慢兜底：exiftool 直接读文件路径（无需临时文件）
        try:
            result = subprocess.run(
                [
                    "exiftool",
                    "-b",
                    "-EmbeddedVideoFile",
                    "-MicroVideo",
                    str(path),
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and len(result.stdout) > 1000:
                logger.debug("视频提取：exiftool 兜底成功")
                return result.stdout
            if result.stderr:
                logger.debug(
                    f"exiftool 视频提取无结果: {result.stderr.decode(errors='replace')}"
                )
            return None
        except Exception:
            logger.exception("视频提取失败")
            return None

    @classmethod
    def _fast_extract_mp4_from_mmap(cls, mm: mmap.mmap, file_size: int) -> bytes | None:
        """
        在 mmap 对象上执行快路径提取：re.search / find 均原生支持 mmap。
        只拷贝最终视频切片，而非持有整个文件。
        """

        def _validate(data: bytes) -> bytes | None:
            return data if len(data) > 1000 and b"ftyp" in data[:32] else None

        # 策略 1：Google MicroVideoOffset
        match = _MICRO_VIDEO_OFFSET_RE.search(mm)
        if match:
            offset = int(match.group(1))
            if 0 < offset < file_size:
                result = _validate(bytes(mm[file_size - offset :]))
                if result:
                    return result

        # 策略 2：Google/Samsung MotionPhotoOffset
        match = _MOTION_PHOTO_OFFSET_RE.search(mm)
        if match:
            offset = int(match.group(1))
            if 0 < offset < file_size:
                result = _validate(bytes(mm[file_size - offset :]))
                if result:
                    return result

        # 策略 3：二进制 ftyp box 搜索（从后半段搜索避免 EXIF 误匹配）
        search_start = file_size // 2
        for sig in _FTYP_SIGNATURES:
            idx = mm.find(sig, search_start)
            if idx != -1:
                start = idx - 4  # ftyp 前 4 字节是 box size
                if start >= search_start:
                    result = _validate(bytes(mm[start:]))
                    if result:
                        return result

        return None

    # ==================================================================
    # 同步核心 — 基于字节（向后兼容包装）
    # ==================================================================

    @classmethod
    def _write_temp(cls, image_buffer: bytes, suffix: str) -> Path:
        """写入临时文件，保留正确后缀供 ExifTool 识别格式"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image_buffer)
            tmp_name = tmp.name
        return Path(tmp_name)

    @classmethod
    def _extract_sync(cls, image_buffer: bytes, suffix: str) -> ImageMetadata:
        """字节版包装：写临时文件 → 调用路径版 → 清理。"""
        temp_path: Path | None = None
        try:
            temp_path = cls._write_temp(image_buffer, suffix)
            return cls._extract_from_file(temp_path)
        finally:
            if temp_path and temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()

    @classmethod
    def _thumbnail_sync(cls, buffer: bytes, max_side: int) -> bytes:
        """字节版包装：写临时文件 → 调用路径版 → 清理。"""
        if not buffer:
            raise ThumbnailGenerationError(message="接收到的图片字节流为空")

        temp_path: Path | None = None
        try:
            temp_path = cls._write_temp(buffer, ".tmp")
            return cls._thumbnail_from_file(temp_path, max_side)
        finally:
            if temp_path and temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()

    @classmethod
    def _extract_video_sync(cls, image_buffer: bytes, suffix: str) -> bytes | None:
        """字节版包装：写临时文件 → 调用路径版 → 清理。"""
        temp_path: Path | None = None
        try:
            temp_path = cls._write_temp(image_buffer, suffix)
            return cls._extract_video_from_file(temp_path, suffix)
        finally:
            if temp_path and temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()

    @classmethod
    def _prepare_video_sync(
        cls,
        video_bytes: bytes,
        input_suffix: str,
    ) -> bytes | None:
        """字节版包装：写临时文件 → 调用路径版 → 清理。"""
        input_path: Path | None = None
        try:
            input_path = cls._write_temp(video_bytes, input_suffix)
            return cls._prepare_video_from_file(input_path, input_suffix)
        finally:
            if input_path and input_path.exists():
                with contextlib.suppress(OSError):
                    input_path.unlink()

    @classmethod
    def _extract_content_identifier_sync(
        cls, file_bytes: bytes, suffix: str
    ) -> str | None:
        """从 HEIC/MOV 文件中提取 Apple Live Photo 的 ContentIdentifier。"""
        temp_path = cls._write_temp(file_bytes, suffix)
        try:
            raw = cls._call_exiftool(temp_path)
            for key in (
                "Apple:ContentIdentifier",
                "Keys:ContentIdentifier",
                "QuickTime:ContentIdentifier",
            ):
                if raw.get(key):
                    return str(raw[key])
            for key, value in raw.items():
                if key.endswith("ContentIdentifier") and value:
                    return str(value)
            return None
        except Exception:
            logger.exception("ContentIdentifier 提取失败")
            return None
        finally:
            with contextlib.suppress(OSError):
                temp_path.unlink()

    # ==================================================================
    # 内部工具方法
    # ==================================================================

    @classmethod
    def _call_exiftool(cls, path: Path) -> dict[str, Any]:
        with ExifToolHelper() as et:
            metadata_list: list[dict[str, Any]] = et.get_metadata(str(path))
        return metadata_list[0] if metadata_list else {}

    @classmethod
    def _needs_transcode(cls, path: Path) -> bool:
        """用 ffprobe 探测视频编码，非 H.264 则需要转码"""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name",
                    "-of",
                    "csv=p=0",
                    str(path),
                ],
                capture_output=True,
                timeout=10,
            )
            codec = result.stdout.decode().strip().lower()
            logger.debug(f"ffprobe 探测编码: {codec}")
            return codec != "h264"
        except Exception:
            logger.debug("ffprobe 探测失败，保守选择转码")
            return True

    # ------------------------------------------------------------------
    # 数据清洗
    # ------------------------------------------------------------------

    @classmethod
    def _filter_binary(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """移除缩略图、预览图等二进制大字段"""
        return {k: v for k, v in raw.items() if k.split(":")[-1] not in _BINARY_KEYS}

    @classmethod
    def _flatten_by_priority(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """按命名空间优先级展平字典。"""
        ns_buckets: dict[str, dict[str, Any]] = defaultdict(dict)
        flat: dict[str, Any] = {}

        for full_key, value in raw.items():
            if ":" in full_key:
                ns, tag = full_key.split(":", 1)
                ns_buckets[ns][tag] = value
            else:
                flat[full_key] = value

        for ns, bucket in ns_buckets.items():
            if ns not in _PRIORITY_SET:
                flat.update(bucket)

        for ns in _NS_PRIORITY:
            if ns in ns_buckets:
                flat.update(ns_buckets[ns])

        return flat
