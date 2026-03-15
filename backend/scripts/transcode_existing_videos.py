"""
一次性脚本：将 uploads/videos/ 下的现有视频统一转为 H.264 MP4 + faststart。

- .mov 文件 → 转码为 H.264 MP4（删除原 .mov）
- .mp4 文件 → remux 确保 moov 前置（原地覆盖）

⚠️  此脚本应在 alembic 迁移之前运行。需要系统已安装 ffmpeg。

用法:
    cd backend && python -m scripts.transcode_existing_videos           # dry-run（仅预览）
    cd backend && python -m scripts.transcode_existing_videos --apply   # 实际执行
"""

import argparse
import contextlib
import subprocess
import tempfile
from pathlib import Path

from loguru import logger

VIDEOS_DIR = Path("uploads/videos")


def _transcode_mov(src: Path, dst: Path) -> bool:
    """MOV → H.264 MP4 转码"""
    cmd = [
        "ffmpeg", "-i", str(src),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-y", str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        logger.error(
            f"ffmpeg 转码失败 {src}: {result.stderr.decode(errors='replace')[:500]}"
        )
        return False
    return True


def _remux_mp4(src: Path) -> bool:
    """MP4 remux 确保 moov 前置（faststart）"""
    # 写入临时文件，完成后替换原文件
    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".mp4", dir=src.parent)
    tmp_path = Path(tmp_path_str)
    try:
        import os

        os.close(tmp_fd)
        cmd = [
            "ffmpeg", "-i", str(src),
            "-c", "copy",
            "-movflags", "+faststart",
            "-y", str(tmp_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            logger.error(
                f"ffmpeg remux 失败 {src}: {result.stderr.decode(errors='replace')[:500]}"
            )
            return False
        # 替换原文件
        tmp_path.replace(src)
        return True
    except Exception:
        logger.exception(f"remux 处理失败 {src}")
        return False
    finally:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)


def main(*, apply: bool = False) -> None:
    if not VIDEOS_DIR.exists():
        logger.info(f"[transcode] 目录不存在: {VIDEOS_DIR}")
        return

    mov_files = sorted(VIDEOS_DIR.glob("*.mov"))
    mp4_files = sorted(VIDEOS_DIR.glob("*.mp4"))

    logger.info(
        f"[transcode] 扫描完成: {len(mov_files)} 个 .mov, {len(mp4_files)} 个 .mp4, apply={apply}"
    )

    if not mov_files and not mp4_files:
        logger.info("[transcode] 没有需要处理的视频文件")
        return

    transcoded, remuxed, failed = 0, 0, 0

    # 处理 MOV → MP4 转码
    for mov in mov_files:
        mp4_dst = mov.with_suffix(".mp4")
        logger.info(f"  [transcode] {mov.name} → {mp4_dst.name}")

        if not apply:
            transcoded += 1
            continue

        try:
            if _transcode_mov(mov, mp4_dst):
                mov.unlink()
                transcoded += 1
                logger.info(f"  [transcode] 转码成功，已删除原文件: {mov.name}")
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception(f"  [transcode] 转码失败: {mov.name}")

    # 处理 MP4 remux（确保 moov 前置）
    # 重新扫描以包含刚转码的文件
    if apply:
        mp4_files = sorted(VIDEOS_DIR.glob("*.mp4"))

    for mp4 in mp4_files:
        logger.info(f"  [remux] {mp4.name} → faststart")

        if not apply:
            remuxed += 1
            continue

        try:
            if _remux_mp4(mp4):
                remuxed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception(f"  [remux] 处理失败: {mp4.name}")

    logger.info(
        f"[transcode] 完成: 转码={transcoded}, remux={remuxed}, 失败={failed}"
    )
    if not apply and (transcoded > 0 or remuxed > 0):
        logger.info("[transcode] 以上为预览模式，添加 --apply 参数以实际执行")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="将现有视频统一转为 H.264 MP4 + faststart"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际执行转码（默认仅预览）",
    )
    args = parser.parse_args()
    main(apply=args.apply)
