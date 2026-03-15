"""
arq Worker 配置模块

定义后台任务函数和 WorkerSettings，由独立进程执行：
    arq core.worker.WorkerSettings
"""

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID

import aiofiles
from arq.connections import RedisSettings
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import core.all_models  # noqa: F401
from core.config import settings
from core.storage import get_storage_service
from services.photo_story.repos.photo_repo import PhotoRepo
from services.photo_story.schemas.photo_schema import PhotoWorkerUpdate
from services.photo_story.utils.image_util import ImageUtil

# ---------------------------------------------------------------------------
# Worker 内部数据库会话工厂（独立于 FastAPI 请求生命周期）
# ---------------------------------------------------------------------------

_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=5,
)

_AsyncSession = async_sessionmaker[AsyncSession](
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


async def _read_file_bytes(object_key: str) -> bytes:
    """
    根据 object_key 读取原图字节流。
    - 开发环境：object_key 即本地相对路径（如 uploads/originals/xxx.jpg）
    - 生产环境：通过 OSS SDK 下载（待 AliyunOSSStrategy 实现后扩展）
    """
    if settings.ENV == "dev":
        async with aiofiles.open(object_key, "rb") as f:
            return await f.read()

    # 生产环境：从 OSS 下载原图（object_key 为 OSS 对象路径）
    # 此处预留扩展点，待 AliyunOSSStrategy 补充 download_bytes 方法后实现
    raise NotImplementedError(f"生产环境原图下载尚未实现，object_key={object_key}")


def _infer_suffix(object_key: str) -> str:
    """从 object_key 推断文件后缀，默认 .jpg"""
    suffix = Path(object_key).suffix.lower()
    return suffix if suffix else ".jpg"


# ---------------------------------------------------------------------------
# 任务函数
# ---------------------------------------------------------------------------


async def parse_photo_exif(
    ctx: dict[str, Any],
    photo_id: str,
    object_key: str,
    pre_video_key: str | None = None,
) -> None:
    """
    后台任务：提取照片 EXIF 元数据并生成缩略图，完成后更新数据库记录。

    - 数据库中不再存在物理的 `status` 字段。
    - 成功时：回写真实的 exif_data 字典。
    - 无数据时：回写空字典 `{}`。
    - 失败时：回写错误标识字典 `{"_error": "..."}`。
    - 只要 exif_data 不为 null，前端就认为处理流程已结束。
    """
    logger.info(f"[arq] 开始处理照片 EXIF，photo_id={photo_id}")

    suffix = _infer_suffix(object_key)

    metadata = None
    has_video = False

    # ------------------------------------------------------------------
    # 纯计算阶段：不持有任何 DB 连接
    # ------------------------------------------------------------------
    try:
        # 1. 读取原图字节流
        file_bytes = await _read_file_bytes(object_key)

        metadata, thumb_bytes = await asyncio.gather(
            ImageUtil.extract_metadata(file_bytes, suffix=suffix),
            ImageUtil.generate_thumbnail(file_bytes),
            return_exceptions=True,
        )

        # 仅当缩略图成功生成时才执行上传
        if not isinstance(thumb_bytes, Exception) and thumb_bytes is not None:
            try:
                storage = get_storage_service()
                await storage.upload_bytes(
                    thumb_bytes, suffix=".webp", stem=Path(object_key).stem
                )
            except Exception:
                logger.exception(
                    f"[arq] 缩略图上传失败，photo_id={photo_id}, object_key={object_key}"
                )

    except Exception as e:
        logger.exception(
            f"[arq] EXIF 处理失败，photo_id={photo_id}, object_key={object_key}"
        )
        # 直接组装失败 DTO 并执行数据库回写，终止执行
        update_data = PhotoWorkerUpdate(
            width=None,
            height=None,
            taken_at=None,
            exif_data={"_error": f"read_file_failed: {e!s}"},
            has_video=False,
            location_wkt=None,
        )
        async with _AsyncSession() as db:
            await PhotoRepo.update_after_processing(db, UUID(photo_id), update_data)
        return
    metadata_isvalid = not isinstance(metadata, Exception) and metadata is not None
    location_wkt: str | None = None
    if (
        metadata_isvalid
        and metadata.latitude is not None
        and metadata.longitude is not None
        and not (metadata.latitude == 0.0 and metadata.longitude == 0.0)
    ):
        location_wkt = f"POINT({metadata.longitude} {metadata.latitude})"

    # ------------------------------------------------------------------
    # 动态照片视频处理（统一转码为 H.264 MP4 + faststart）
    # ------------------------------------------------------------------
    if pre_video_key:
        # iOS Live Photo：读取临时上传的 MOV → 转码 → 覆盖上传 MP4 → 删除原始 MOV
        try:
            mov_bytes = await _read_file_bytes(pre_video_key)
            mp4_bytes = await ImageUtil.prepare_video_for_web(
                mov_bytes, ".mov"
            )
            if mp4_bytes:
                storage = get_storage_service()
                await storage.upload_bytes(
                    mp4_bytes,
                    suffix=".mp4",
                    subdir="videos",
                    stem=Path(object_key).stem,
                )
                has_video = True
            await get_storage_service().delete_file(pre_video_key)
        except Exception:
            logger.exception(
                f"[arq] iOS 视频转码失败，photo_id={photo_id}, pre_video_key={pre_video_key}"
            )
    elif metadata_isvalid:
        exif = metadata.exif_data or {}
        is_motion = (
            str(exif.get("MotionPhoto")) == "1"
            or str(exif.get("MicroVideo")) == "1"
        )
        if is_motion:
            video_bytes = await ImageUtil.extract_embedded_video(file_bytes, suffix)
            if video_bytes:
                try:
                    mp4_bytes = await ImageUtil.prepare_video_for_web(
                        video_bytes, ".mp4"
                    )
                    if mp4_bytes:
                        storage = get_storage_service()
                        await storage.upload_bytes(
                            mp4_bytes,
                            suffix=".mp4",
                            subdir="videos",
                            stem=Path(object_key).stem,
                        )
                        has_video = True
                except Exception:
                    logger.exception(
                        f"[arq] Android 视频处理失败，photo_id={photo_id}, object_key={object_key}"
                    )

    # 5. 组装最终回写 DTO，保证任务总能结束 processing 状态
    # 成功提取到元数据时，None 需转为 {}，明确告诉前端处理已结束但没有可展示 EXIF

    update_data = PhotoWorkerUpdate(
        width=metadata.width if metadata_isvalid else 0,
        height=metadata.height if metadata_isvalid else 0,
        taken_at=metadata.taken_at if metadata_isvalid else None,
        exif_data=metadata.exif_data
        if metadata_isvalid
        else {"_error": "worker_processing_failed"},
        has_video=has_video,
        location_wkt=location_wkt,
    )

    # ------------------------------------------------------------------
    # 短事务阶段：仅一次 UPDATE，立即释放连接
    # ------------------------------------------------------------------
    async with _AsyncSession() as db:
        try:
            await PhotoRepo.update_after_processing(db, UUID(photo_id), update_data)
        except Exception:
            await db.rollback()
            raise


async def delete_oss_files(ctx: dict[str, Any], keys: list[str]) -> None:
    """
    后台任务：批量删除 OSS / 本地存储 中的文件。
    具备重试机制与异常隔离，尽最大努力清理垃圾文件。
    """
    if not keys:
        return

    logger.info(f"[arq] 开始后台清理 {len(keys)} 个文件")
    storage = get_storage_service()

    # 并发向 OSS 发起删除请求
    tasks = [storage.delete_file(key) for key in keys]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 错误统计与记录
    error_count = 0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            error_count += 1
            logger.warning(f"[arq] 文件清理失败 [key={keys[i]}]: {result!s}")

    if error_count > 0:
        # 如果有失败的，抛出异常让 arq 触发重试机制（根据配置重试几次）
        raise RuntimeError(f"有 {error_count} 个文件清理失败，触发 arq 重试")

    logger.info(f"[arq] {len(keys)} 个文件清理完成")


# ---------------------------------------------------------------------------
# WorkerSettings：arq 通过此类启动 Worker 进程
# ---------------------------------------------------------------------------


class WorkerSettings:
    """
    arq Worker 配置类。

    启动命令：
        cd backend && arq core.worker.WorkerSettings
    """

    # 注册的任务函数列表
    functions = [parse_photo_exif,delete_oss_files]

    # Redis 连接配置（从 settings.REDIS_URL 读取）
    redis_settings = RedisSettings.from_dsn(settings.REDIS_ARQ_URL)

    # 并发任务数上限
    max_jobs = 10

    # 单个任务超时时间（秒）
    job_timeout = 120

    # 任务失败后最大重试次数（arq 默认 5 次，此处收紧为 3 次）
    max_tries = 3

    # Worker 健康检查间隔（秒）
    health_check_interval = 30

    # 定时任务（按需启用，示例：每天凌晨清理孤儿任务）
    # cron_jobs = [
    #     cron(cleanup_orphan_jobs, hour=3, minute=0),
    # ]

    @staticmethod
    async def on_startup(ctx: dict[str, Any]) -> None:
        """Worker 进程启动时执行：预热数据库连接池"""
        from sqlalchemy import text

        async with _engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ [arq Worker] 数据库连接池已预热")

    @staticmethod
    async def on_shutdown(ctx: dict[str, Any]) -> None:
        """Worker 进程关闭时执行：释放数据库连接池"""
        await _engine.dispose()
        logger.info("✅ [arq Worker] 数据库连接池已释放")
