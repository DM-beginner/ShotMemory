"""
一次性脚本：重新解析 exif_data 缺失或失败的照片。

用法:
    cd backend && python -m scripts.reparse_exif              # 仅处理 NULL
    cd backend && python -m scripts.reparse_exif --include-failed  # 同时处理失败记录
"""

import argparse
import asyncio
from pathlib import Path
from uuid import UUID

from loguru import logger
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from core.storage import get_storage_service
from core.worker import _infer_suffix, _read_file_bytes
from services.photo_story.models.photo_model import Photo
from services.photo_story.repos.photo_repo import PhotoRepo
from services.photo_story.schemas.photo_schema import PhotoWorkerUpdate
from services.photo_story.utils.image_util import ImageUtil


async def _process_one(
    session_factory: async_sessionmaker[AsyncSession],
    photo_id: UUID,
    object_key: str,
) -> bool:
    """处理单张照片，返回是否成功。"""
    suffix = _infer_suffix(object_key)

    # ---- 纯计算阶段（不持有 DB 连接）----
    file_bytes = await _read_file_bytes(object_key)

    metadata, thumb_bytes = await asyncio.gather(
        ImageUtil.extract_metadata(file_bytes, suffix=suffix),
        ImageUtil.generate_thumbnail(file_bytes),
        return_exceptions=True,
    )

    if not isinstance(thumb_bytes, Exception) and thumb_bytes is not None:
        try:
            storage = get_storage_service()
            await storage.upload_bytes(
                thumb_bytes, suffix=".webp", stem=Path(object_key).stem
            )
        except Exception:
            logger.exception(f"[reparse] 缩略图上传失败 photo_id={photo_id}")

    metadata_ok = not isinstance(metadata, Exception) and metadata is not None

    location_wkt: str | None = None
    if metadata_ok and metadata.latitude is not None and metadata.longitude is not None:
        location_wkt = f"POINT({metadata.longitude} {metadata.latitude})"

    update_data = PhotoWorkerUpdate(
        width=metadata.width if metadata_ok else 0,
        height=metadata.height if metadata_ok else 0,
        taken_at=metadata.taken_at if metadata_ok else None,
        exif_data=metadata.exif_data if metadata_ok else {"_error": "reparse_failed"},
        location_wkt=location_wkt,
    )

    # ---- 短事务阶段 ----
    async with session_factory() as db:
        await PhotoRepo.update_after_processing(db, photo_id, update_data)

    return True


async def main(include_failed: bool = False) -> None:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # ---- 查询目标照片 ----
    async with session_factory() as db:
        conditions = [Photo.exif_data.is_(None)]
        if include_failed:
            conditions.append(Photo.exif_data.op("->>")(text("'_error'")).isnot(None))
        stmt = select(Photo.id, Photo.object_key).where(or_(*conditions))
        rows = (await db.execute(stmt)).all()

    total = len(rows)
    if total == 0:
        logger.info("[reparse] 没有需要重新处理的照片")
        await engine.dispose()
        return

    logger.info(
        f"[reparse] 找到 {total} 张待处理照片 (include_failed={include_failed})"
    )

    ok, fail = 0, 0
    for idx, (photo_id, object_key) in enumerate(rows, 1):
        try:
            await _process_one(session_factory, photo_id, object_key)
            ok += 1
            logger.info(f"[{idx}/{total}] photo_id={photo_id} done")
        except Exception as exc:
            fail += 1
            logger.error(f"[{idx}/{total}] photo_id={photo_id} failed: {exc}")

    logger.info(f"[reparse] 完成: 成功={ok}, 失败={fail}, 总计={total}")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="重新解析照片 EXIF 数据")
    parser.add_argument(
        "--include-failed",
        action="store_true",
        help="同时处理 exif_data 含 _error 标记的失败记录",
    )
    args = parser.parse_args()
    asyncio.run(main(include_failed=args.include_failed))
