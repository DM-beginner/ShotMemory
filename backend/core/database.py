from typing import Annotated

from arq.connections import ArqRedis
from fastapi import Depends, Request
from redis import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "dev",
    pool_pre_ping=True,  # 每次从池中取连接时先测试连接是否有效
    pool_recycle=3600,  # 1小时后回收连接，防止数据库主动断开
    pool_size=15,  # 连接池大小
    max_overflow=10,  # 超出pool_size后最多再创建10个连接
    pool_timeout=30,  # 获取连接的超时时间（秒）
)

# [AsyncSession]泛型参数确保了类型安全，避免隐式类型转换和潜在的运行时错误。
AsyncSessionLocal = async_sessionmaker[AsyncSession](
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 极其重要！防止 commit 后属性访问触发额外的 SQL 查询
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            from loguru import logger

            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        # finally:
        #     await session.close()
        # async with 自带了退出时自动调用close()的功能


# 依赖注入类型别名
SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_redis(request: Request) -> ArqRedis:
    """
    arq Redis 连接池依赖。

    从 app.state 中取出 lifespan 阶段建立的连接池，
    与 get_db 风格完全一致，无需模块级全局变量。
    """
    return request.app.state.arq_queue


RedisDep = Annotated[ArqRedis, Depends(get_redis)]


async def get_redis_cache(request: Request) -> Redis:
    """依赖：获取缓存 Redis"""
    return request.app.state.redis_cache


async def warm_up():
    """预热数据库连接池"""
    from loguru import logger

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection pool warmed up")
    except Exception as e:
        logger.error(f"❌ Failed to warm up database: {e}")
        raise


async def close_db():
    """关闭数据库连接池"""
    from loguru import logger

    await engine.dispose()
    logger.info("✅ Database connection pool disposed")
