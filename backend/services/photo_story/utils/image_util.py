import asyncio
import contextlib
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

    # ------------------------------------------------------------------
    # 公开异步入口
    # ------------------------------------------------------------------

    @classmethod
    async def extract_metadata(
        cls, image_buffer: bytes, suffix: str = ".jpg"
    ) -> ImageMetadata:
        """
        异步入口：将同步的 ExifTool 调用放到线程池执行，避免阻塞事件循环。
        suffix 应与文件实际格式匹配（如 .png / .webp），ExifTool 依赖后缀识别格式。
        """
        return await asyncio.to_thread(cls._extract_sync, image_buffer, suffix)

    @classmethod
    async def generate_thumbnail(cls, buffer: bytes, max_side: int = 400) -> bytes:
        """
        异步入口：将同步的 Pillow 压缩操作放到线程池执行，避免阻塞事件循环。
        返回体积压缩到极限的 WebP 格式缩略图字节流。
        """
        return await asyncio.to_thread(cls._thumbnail_sync, buffer, max_side)

    @classmethod
    async def extract_embedded_video(
        cls, image_buffer: bytes, suffix: str = ".jpg"
    ) -> bytes | None:
        """
        异步入口：提取动态照片中嵌入的视频流。
        支持 Samsung/Google/OPPO 的 MotionPhoto 和 MicroVideo 格式。
        """
        return await asyncio.to_thread(cls._extract_video_sync, image_buffer, suffix)

    @classmethod
    async def extract_content_identifier(
        cls, file_bytes: bytes, suffix: str
    ) -> str | None:
        """
        异步入口：提取 Apple Live Photo 的 ContentIdentifier UUID。
        """
        return await asyncio.to_thread(
            cls._extract_content_identifier_sync, file_bytes, suffix
        )

    @classmethod
    async def prepare_video_for_web(
        cls,
        video_bytes: bytes,
        input_suffix: str,
    ) -> bytes | None:
        """
        异步入口：将视频转码/remux 为 H.264 MP4 + faststart。
        内部自动探测编码格式：H.265/HEVC → 转码，H.264 → 仅 remux。
        """
        return await asyncio.to_thread(
            cls._prepare_video_sync, video_bytes, input_suffix
        )

    # ------------------------------------------------------------------
    # 同步核心（运行在 asyncio.to_thread 的子线程中）
    # ------------------------------------------------------------------

    @classmethod
    def _write_temp(cls, image_buffer: bytes, suffix: str) -> Path:
        """写入临时文件，保留正确后缀供 ExifTool 识别格式"""
        # delete=False：Windows 下不允许两个进程同时打开同一临时文件
        # 这里使用 with 语法上下文管理器，打开一个带有指定后缀（suffix）的临时文件；
        # tempfile.NamedTemporaryFile(delete=False, suffix=suffix) 创建一个临时文件对象：
        # - delete=False 表示文件关闭后不会自动删除，方便后续用 Path(tmp.name) 访问、处理，再手动删除；
        # - suffix=suffix 指定文件后缀，便于 ExifTool 按正确格式识别图片；
        # with ... as tmp: 可以确保文件写入完成后自动关闭文件句柄，防止资源泄漏。
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image_buffer)
            tmp_name = tmp.name
        return Path(tmp_name)

    @classmethod
    def _call_exiftool(cls, path: Path) -> dict[str, Any]:
        # ExifToolHelper() 是 pyexiftool 提供的简化封装，管理 exiftool 进程的生命周期，方便地批量解析文件元数据。
        # 推荐用 with 上下文管理器，自动关闭进程资源。

        with ExifToolHelper() as et:
            # et.get_metadata(str(path)) 会返回一个列表（list[dict]），
            # 列表中每个元素代表一张图片（可批量对多个文件），此处只解析单个 path，所以通常只有一个元素。
            # 每个元素是该图片的所有元数据字段组成的字典（tag: value）。
            metadata_list: list[dict[str, Any]] = et.get_metadata(str(path))

        # 因为这里只传入一个图片路径，所以只关心结果列表的第一个元素（metadata_list[0]）。
        # 出于保险考虑，如果结果为空列表（如文件损坏或无 EXIF），则返回空字典 {}。
        return metadata_list[0] if metadata_list else {}

    @classmethod
    def _extract_sync(cls, image_buffer: bytes, suffix: str) -> ImageMetadata:
        temp_path: Path | None = None
        try:
            temp_path = cls._write_temp(image_buffer, suffix)

            # 1. 获取原始大字典
            raw_exif = cls._call_exiftool(temp_path)

            # 2. 剔除毒瘤（二进制大图）
            filtered = cls._filter_binary(raw_exif)

            # 3. 展平字典，解决命名空间冲突
            flat = cls._flatten_by_priority(filtered)

            # 4. 极致优雅的收尾：直接喂给 Pydantic 模型！
            # 我们之前写的 map_exif_keys 验证器会自动接管解析、回退和清洗工作。
            return ImageMetadata.model_validate(flat)
        except Exception:
            logger.exception("EXIF 提取过程发生致命崩溃，执行极其安全的全局兜底")
            # 极端异常情况下，返回一个全为默认值/None的干净模型，防止队列死锁
            return ImageMetadata()
        finally:
            if temp_path and temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()

    @classmethod
    def _thumbnail_sync(cls, buffer: bytes, max_side: int) -> bytes:
        """
        同步 Pillow 压缩核心：
        - 自动修复 EXIF 旋转魔咒（关键优化）
        - thumbnail() 等比缩放，完美适配瀑布流
        - WebP quality=60, method=6 极限压缩体积
        """
        if not buffer:
            raise ThumbnailGenerationError(message = "接收到的图片字节流为空")

        try:
            with Image.open(BytesIO(buffer)) as img:
                img.load()  # 提前触发解压，捕获截断异常

                # 优化 1：强制根据 EXIF 信息旋转图片，防止瀑布流出现“躺着”的竖图
                img = ImageOps.exif_transpose(img)

                # 优化 2：统一色彩模式，防止 CMYK 或带透明通道的图引发异常
                img = img.convert("RGBA") if img.mode in ("RGBA", "P") else img.convert("RGB")

                # 等比缩放，不破坏原图宽高比
                img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

                # 1. 内存内保存，我们不直接写硬盘，而是先在内存缓冲区 (BytesIO) 中构建图片数据，提高 I/O 速度。
                with BytesIO() as out:
                    img.save(
                        out,
                        format="WEBP",  # 使用 WebP 格式，在相同质量下体积通常比 JPG 小 30% 以上。
                        quality=60,  # 质量分，60 是瀑布流缩略图的“黄金平衡点”，再低就会有噪点。
                        method=6,  # 关键参数：WebP 编码器的压缩方法等级（0-6）。
                    )
                    # 3. 获取字节流
                    return out.getvalue()

        except Image.DecompressionBombError as e:
            """
                虽然图片文件本身经过压缩后可能只有几百 KB（存储在磁盘上时），
                但当你使用 img.load() 或进行处理时，Pillow 需要在 RAM（内存） 中将其还原为未经压缩的原始像素矩阵。
                计算公式：内存占用=Width * Height * 4 字节（对于 RGBA 模式）。
                后果：一张 100,000 * 100,000 的图片，解压后大约需要 37.2 GB 的内存。
                这会瞬间导致服务器 OOM (Out Of Memory) 崩溃。
                Pillow 默认的阈值通常是 89,478,485 像素（约 9459x9459 像素）。
                超过这个限制，Pillow 就会抛出 DecompressionBombError。
                我们在代码中捕获它并抛出 ThumbnailGenerationError，是为了保护 Worker 进程不被恶意图片拖垮。
            """
            logger.error(f"遭遇图片解压炸弹，拒绝处理: {e!s}")
            raise ThumbnailGenerationError(message = "图片分辨率过大，拒绝处理") from e
        except Exception as e:
            # 拦截不可预见的物理级错误
            # 1. 损坏的图片 (Corrupted Image)：文件传了一半断了，或者文件头信息是乱码，Pillow 解码器会崩溃。
            # 2. 内存不足 (MemoryError)：虽然没到炸弹级别，但当时服务器内存刚好满了。
            # 3. 不支持的特殊模式：某些罕见的医疗级 TIFF 或 16 位 HDR 图片，Pillow 在保存为 WebP 时可能内部报错。
            logger.exception("Pillow 生成缩略图发生不可恢复异常")
            raise ThumbnailGenerationError(message = f"缩略图生成失败: {e!s}") from e

    @classmethod
    def _fast_extract_mp4_from_memory(cls, image_buffer: bytes) -> bytes | None:
        """
        纯 Python 内存提取：直接从图片字节流中切出嵌入的 MP4 视频。
        零磁盘 I/O，零进程启动。覆盖 Google/Samsung/OPPO 等主流 Android 厂商格式。
        """
        if not image_buffer or len(image_buffer) < 1000:
            return None

        def _validate(data: bytes) -> bytes | None:
            """校验切出的数据是否为合法 MP4（ftyp box 在头部 32 字节内）"""
            return data if len(data) > 1000 and b"ftyp" in data[:32] else None

        # 策略 1：Google MicroVideoOffset（最常见）
        match = _MICRO_VIDEO_OFFSET_RE.search(image_buffer)
        if match:
            offset = int(match.group(1))
            if 0 < offset < len(image_buffer):
                result = _validate(image_buffer[-offset:])
                if result:
                    return result

        # 策略 2：Google/Samsung MotionPhotoOffset（较新格式）
        match = _MOTION_PHOTO_OFFSET_RE.search(image_buffer)
        if match:
            offset = int(match.group(1))
            if 0 < offset < len(image_buffer):
                result = _validate(image_buffer[-offset:])
                if result:
                    return result

        # 策略 3：二进制 ftyp box 搜索（万能兜底，从后半段搜索避免 EXIF 误匹配）
        search_start = len(image_buffer) // 2
        for sig in _FTYP_SIGNATURES:
            idx = image_buffer.find(sig, search_start)
            if idx != -1:
                start = idx - 4  # ftyp 前 4 字节是 box size
                if start >= search_start:
                    result = _validate(image_buffer[start:])
                    if result:
                        return result

        return None

    @classmethod
    def _extract_video_sync(cls, image_buffer: bytes, suffix: str) -> bytes | None:
        """
        双轨制提取嵌入视频：
        快路径 → _fast_extract_mp4_from_memory（纯内存，零开销）
        慢兜底 → exiftool subprocess（处理快路径未覆盖的边缘格式）
        """
        # 快路径：纯 Python 内存提取
        try:
            fast_result = cls._fast_extract_mp4_from_memory(image_buffer)
            if fast_result:
                logger.debug("视频提取：纯 Python 快路径命中")
                return fast_result
        except Exception:
            logger.debug("视频提取：快路径异常，降级 exiftool")

        # 慢兜底：exiftool 子进程提取
        temp_path = cls._write_temp(image_buffer, suffix)
        try:
            result = subprocess.run(
                ["exiftool", "-b", "-EmbeddedVideoFile", "-MicroVideo", str(temp_path)],
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
        finally:
            with contextlib.suppress(OSError):
                temp_path.unlink()

    @classmethod
    def _extract_content_identifier_sync(
        cls, file_bytes: bytes, suffix: str
    ) -> str | None:
        """
        从 HEIC/MOV 文件中提取 Apple Live Photo 的 ContentIdentifier。
        查找键：Apple:ContentIdentifier、Keys:ContentIdentifier、ContentIdentifier。
        """
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
            # 展平后的 fallback
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

    @classmethod
    def _needs_transcode(cls, path: Path) -> bool:
        """用 ffprobe 探测视频编码，非 H.264 则需要转码"""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=codec_name",
                    "-of", "csv=p=0",
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

    @classmethod
    def _prepare_video_sync(
        cls,
        video_bytes: bytes,
        input_suffix: str,
    ) -> bytes | None:
        """
        同步核心：使用 ffmpeg 将视频转为 H.264 MP4 + faststart。
        自动探测编码：H.264 → remux（-c copy，瞬间完成），其余 → 转码。
        """
        input_path = cls._write_temp(video_bytes, input_suffix)
        # 给输出文件加一个 _web 的小尾巴，确保它是一个全新的物理文件
        output_path = input_path.with_name(f"{input_path.stem}_web.mp4")
        try:
            transcode = cls._needs_transcode(input_path)

            if transcode:
                logger.debug("视频需要转码 (非 H.264)")
                cmd = [
                    "ffmpeg", "-i", str(input_path),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    "-y", str(output_path),
                ]
            else:
                logger.debug("视频仅 remux (H.264)")
                cmd = [
                    "ffmpeg", "-i", str(input_path),
                    "-c", "copy",
                    "-movflags", "+faststart",
                    "-y", str(output_path),
                ]

            result = subprocess.run(
                cmd, capture_output=True, timeout=120,
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
                input_path.unlink()
            with contextlib.suppress(OSError):
                output_path.unlink()

    # ------------------------------------------------------------------
    # 数据清洗
    # ------------------------------------------------------------------

    @classmethod
    def _filter_binary(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """移除缩略图、预览图等二进制大字段"""
        return {k: v for k, v in raw.items() if k.split(":")[-1] not in _BINARY_KEYS}

    @classmethod
    def _flatten_by_priority(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """
        按命名空间优先级展平字典。
        采用"从低到高依次覆盖"的策略，利用原生的 dict.update() 实现极致性能。
        """
        ns_buckets: dict[str, dict[str, Any]] = defaultdict(dict)
        flat: dict[str, Any] = {}

        for full_key, value in raw.items():
            if ":" in full_key:
                ns, tag = full_key.split(":", 1)
                ns_buckets[ns][tag] = value
            else:
                # 1. 最底层的垫脚石：没有命名空间的标签（优先级最低）
                flat[full_key] = value

        # 2. 中层：未知命名空间（厂家自定义黑话），覆盖掉无命名的标签
        for ns, bucket in ns_buckets.items():
            if ns not in _PRIORITY_SET:
                flat.update(bucket)

        # 3. 顶层：官方高优命名空间（精华所在）
        # 我们使用 reversed() 倒序遍历！
        # 比如列表是 [EXIF, Composite, XMP]
        # 倒序后变成 [XMP, Composite, EXIF]
        # XMP 先写入，Composite 覆盖 XMP，最后 EXIF 绝对王权，覆盖掉前面所有同名标签！
        for ns in _NS_PRIORITY:
            if ns in ns_buckets:
                flat.update(ns_buckets[ns])

        return flat
