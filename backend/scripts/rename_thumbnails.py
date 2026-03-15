"""
一次性脚本：将现有缩略图文件重命名为与原图同名（stem 一致）。

例如：
  原图  uploads/originals/abc123def456.heic
  旧缩略图 uploads/thumbnails/xxxxyyyyzzzz.webp
  → 新缩略图 uploads/thumbnails/abc123def456.webp

同时更新数据库中的 thumbnail_key。

用法:
    cd backend && python -m scripts.rename_thumbnails           # dry-run（仅预览）
    cd backend && python -m scripts.rename_thumbnails --apply   # 实际执行
"""


import argparse
import asyncio
from pathlib import Path

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from services.photo_story.models.photo_model import Photo


async def main(*, apply: bool = False) -> None:
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # 查询所有同时拥有 object_key 和 thumbnail_key 的照片
    async with session_factory() as db:
        stmt = select(Photo.id, Photo.object_key, Photo.thumbnail_key).where(
            Photo.thumbnail_key.isnot(None),
        )
        rows = (await db.execute(stmt)).all()

    total = len(rows)
    if total == 0:
        logger.info("[rename] 没有需要处理的缩略图")
        await engine.dispose()
        return

    logger.info(f"[rename] 找到 {total} 条缩略图记录，apply={apply}")

    renamed, skipped, failed = 0, 0, 0

    for photo_id, object_key, thumbnail_key in rows:
        original_stem = Path(object_key).stem
        thumb_path = Path(thumbnail_key)
        current_stem = thumb_path.stem

        # 已经同名，跳过
        if current_stem == original_stem:
            skipped += 1
            continue

        new_thumb_name = f"{original_stem}{thumb_path.suffix}"
        new_thumb_key = str(thumb_path.parent / new_thumb_name)

        logger.info(f"  {thumbnail_key} -> {new_thumb_key}")

        if not apply:
            renamed += 1
            continue

        try:
            # 重命名本地文件
            old_file = Path(thumbnail_key)
            new_file = old_file.parent / new_thumb_name

            if old_file.exists():
                if new_file.exists():
                    logger.warning(
                        f"  目标文件已存在，跳过: {new_file}"
                    )
                    skipped += 1
                    continue
                old_file.rename(new_file)
            else:
                logger.warning(f"  源文件不存在，仅更新数据库: {old_file}")

            # 更新数据库
            async with session_factory() as db:
                await db.execute(
                    update(Photo)
                    .where(Photo.id == photo_id)
                    .values(thumbnail_key=new_thumb_key)
                )
                await db.commit()

            renamed += 1
        except Exception:
            failed += 1
            logger.exception(f"  处理失败 photo_id={photo_id}")

    logger.info(
        f"[rename] 完成: 重命名={renamed}, 跳过={skipped}, 失败={failed}, 总计={total}"
    )
    if not apply and renamed > 0:
        logger.info("[rename] 以上为预览模式，添加 --apply 参数以实际执行")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将缩略图重命名为与原图同名")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际执行重命名（默认仅预览）",
    )
    args = parser.parse_args()
    asyncio.run(main(apply=args.apply))
