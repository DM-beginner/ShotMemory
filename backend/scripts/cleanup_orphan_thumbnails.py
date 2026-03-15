"""
一次性脚本：清理数据库中未跟踪的孤儿缩略图文件。

场景：reparse_exif 生成了缩略图但因 Pydantic 校验失败未写入 DB，
      导致磁盘上存在大量无主的 .webp 文件。

用法:
    cd backend && python -m scripts.cleanup_orphan_thumbnails              # 预览（dry-run）
    cd backend && python -m scripts.cleanup_orphan_thumbnails --confirm    # 实际删除
"""

import argparse
import asyncio
from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from services.photo_story.models.photo_model import Photo

THUMBNAILS_DIR = Path("uploads/thumbnails")


async def main(confirm: bool = False) -> None:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # 1. 从 DB 拿到所有 object_key，推导期望的缩略图文件名
    async with session_factory() as db:
        stmt = select(Photo.object_key)
        rows = (await db.execute(stmt)).scalars().all()

    # 从 object_key 的 stem 推导期望的缩略图文件名：abc.heic → abc.webp
    tracked_filenames: set[str] = {f"{Path(key).stem}.webp" for key in rows}

    # 2. 扫描磁盘上的缩略图
    disk_files = {f.name for f in THUMBNAILS_DIR.iterdir() if f.is_file()}

    # 3. 差集 = 孤儿文件
    orphans = disk_files - tracked_filenames

    if not orphans:
        logger.info("没有孤儿缩略图，磁盘与数据库一致")
        await engine.dispose()
        return

    logger.info(f"发现 {len(orphans)} 个孤儿缩略图（磁盘={len(disk_files)}, DB跟踪={len(tracked_filenames)}）")

    if not confirm:
        logger.info("[dry-run] 以下文件将被删除（加 --confirm 实际执行）:")
        for name in sorted(orphans):
            logger.info(f"  {THUMBNAILS_DIR / name}")
        await engine.dispose()
        return

    # 4. 删除
    deleted = 0
    for name in orphans:
        path = THUMBNAILS_DIR / name
        try:
            path.unlink()
            deleted += 1
        except OSError as exc:
            logger.warning(f"删除失败 {path}: {exc}")

    logger.info(f"清理完成: 删除 {deleted}/{len(orphans)} 个孤儿缩略图")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清理数据库未跟踪的孤儿缩略图")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="实际执行删除（默认仅预览）",
    )
    args = parser.parse_args()
    asyncio.run(main(confirm=args.confirm))
