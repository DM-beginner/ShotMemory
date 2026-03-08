# import os
import sys

from loguru import logger

from core.config import settings


def setup_logging():
    # 移除默认的 handler --> 使用logger.add()自定义日志行为
    logger.remove()

    # 1. 控制台输出 (Stdout)
    # 生产环境使用 JSON，开发环境使用彩色文本
    if settings.ENV == "prod":
        logger.add(
            sys.stdout,
            serialize=True,  # 输出 JSON 格式
            level="INFO",
            enqueue=True,  # 异步写入，避免阻塞
            diagnose=False,  # 禁用变量检查，避免超长堆栈输出
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG",
            enqueue=True,  # 异步写入，避免阻塞
            diagnose=False,  # 禁用变量检查，避免超长堆栈输出
        )

    # 2. 文件输出 (File) - 无论环境，都做一份文件备份（可选，K8s环境通常不需要）
    # 确保日志目录存在
    # if settings.ENV == "prod":
    #     log_dir = os.path.dirname(settings.LOG_PATH)
    #     if log_dir and not os.path.exists(log_dir):
    #         os.makedirs(log_dir, exist_ok=True)

    #     logger.add(
    #         settings.LOG_PATH,
    #         rotation=settings.ROTATION,
    #         retention=settings.RETENTION,
    #         compression="zip",  # 轮转后压缩
    #         enqueue=True,
    #         encoding="utf-8",
    #         level="INFO",
    #     )

    return logger
