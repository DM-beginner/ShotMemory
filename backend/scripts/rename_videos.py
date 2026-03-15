"""
一次性脚本：将现有视频文件重命名为与原图同名（stem 一致）。

例如：
  原图  uploads/originals/abc123def456.heic
  旧视频 uploads/videos/abc123def456.mov
  → 新视频 uploads/videos/abc123def456.mp4（后续由 transcode 脚本处理格式转换）

同时更新数据库中的 video_key。

⚠️  此脚本应在 has_video 迁移之前运行（此时 video_key 列仍存在）。

用法:
    cd backend && python -m scripts.rename_videos           # dry-run（仅预览）
    cd backend && python -m scripts.rename_videos --apply   # 实际执行
"""

import argparse
import asyncio
from pathlib import Path

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings


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

    # 查询所有同时拥有 object_key 和 video_key 的照片
    # 注意：迁移前 video_key 列仍存在，这里直接通过 text 查询
    async with session_factory() as db:
        stmt = text(
            "SELECT id, object_key, video_key FROM photo_story.photo WHERE video_key IS NOT NULL"
        )
        rows = (await db.execute(stmt)).all()

    total = len(rows)
    if total == 0:
        logger.info("[rename-videos] 没有需要处理的视频")
        await engine.dispose()
        return

    logger.info(f"[rename-videos] 找到 {total} 条视频记录，apply={apply}")

    renamed, skipped, failed = 0, 0, 0

    for photo_id, object_key, video_key in rows:
        original_stem = Path(object_key).stem
        video_path = Path(video_key)
        current_stem = video_path.stem

        # 已经同名，跳过
        if current_stem == original_stem:
            skipped += 1
            continue

        new_video_name = f"{original_stem}{video_path.suffix}"
        new_video_key = str(video_path.parent / new_video_name)

        logger.info(f"  {video_key} -> {new_video_key}")

        if not apply:
            renamed += 1
            continue

        try:
            # 重命名本地文件
            old_file = Path(video_key)
            new_file = old_file.parent / new_video_name

            if old_file.exists():
                if new_file.exists():
                    logger.warning(f"  目标文件已存在，跳过: {new_file}")
                    skipped += 1
                    continue
                old_file.rename(new_file)
            else:
                logger.warning(f"  源文件不存在，仅更新数据库: {old_file}")

            # 更新数据库
            async with session_factory() as db:
                await db.execute(
                    text(
                        "UPDATE photo_story.photo SET video_key = :new_key WHERE id = :pid"
                    ).bindparams(new_key=new_video_key, pid=photo_id)
                )
                await db.commit()

            renamed += 1
        except Exception:
            failed += 1
            logger.exception(f"  处理失败 photo_id={photo_id}")

    logger.info(
        f"[rename-videos] 完成: 重命名={renamed}, 跳过={skipped}, 失败={failed}, 总计={total}"
    )
    if not apply and renamed > 0:
        logger.info("[rename-videos] 以上为预览模式，添加 --apply 参数以实际执行")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将视频文件重命名为与原图同名")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际执行重命名（默认仅预览）",
    )
    args = parser.parse_args()
    asyncio.run(main(apply=args.apply))
