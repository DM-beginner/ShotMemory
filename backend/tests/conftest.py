"""
测试基础设施 — 独立测试数据库 + 真实 Redis

核心设计：
- 连接 shotmemory_test 数据库（与开发库完全隔离）
- 连接真实 Redis（arq 任务入队、缓存都走真实连接）
- session scope 一次性建表
- HTTP 集成测试每个请求独立 AsyncSession
- 并发测试走独立 session（不共享 AsyncSession）
"""

import os
from collections.abc import AsyncGenerator

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── 在导入 app 之前设置测试数据库 URL ──────────────────────
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:SZtu%40143237@localhost:5432/shotmemory_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import core.all_models  # noqa: E402, F401
from core.base_model import Base  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import get_db  # noqa: E402
from main import create_app  # noqa: E402

# 独立的测试 engine，连接池适配并发测试
test_engine = create_async_engine(
    TEST_DATABASE_URL, echo=False, pool_size=20, max_overflow=10
)
TestSessionLocal = async_sessionmaker[AsyncSession](
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def create_test_app():
    """
    创建测试用 app，手动初始化 Redis state

    为什么需要手动设置 app.state？
    ─────────────────────────────
    httpx 的 ASGITransport 只处理 HTTP 请求/响应，不触发 ASGI Lifespan 事件。
    而 FastAPI 的 lifespan 函数（main.py 里的 async def lifespan）负责：
      - app.state.redis_cache = Redis.from_url(...)     ← 缓存连接
      - app.state.arq_queue  = await create_pool(...)   ← arq 任务队列

    ASGITransport 跳过了这一步，所以 app.state 上这两个属性根本不存在。
    当任何端点通过 RedisDep 访问 request.app.state.arq_queue 时：

        AttributeError: 'State' object has no attribute 'arq_queue'
        ──────────────
        Python 在对象上访问一个不存在的属性时抛出的异常。
        就像你写 user.age，但 user 对象根本没有 age 这个字段。

    所以我们在测试中手动创建真实的 Redis 连接，挂到 app.state 上，
    让端点拿到的是真正能用的 Redis 客户端，而不是一个假的 mock。
    """
    app = create_app()

    # 连接真实 Redis —— 与 main.py lifespan 做的事完全一样
    app.state.redis_cache = Redis.from_url(settings.REDIS_CACHE_URL)
    app.state.arq_queue = await create_pool(
        RedisSettings.from_dsn(settings.REDIS_ARQ_URL)
    )

    return app


async def _cleanup_test_app(app):
    """清理 app 的 Redis 连接"""
    if hasattr(app.state, "redis_cache") and app.state.redis_cache is not None:
        await app.state.redis_cache.aclose()
    if hasattr(app.state, "arq_queue") and app.state.arq_queue is not None:
        await app.state.arq_queue.aclose()


# ── Session-scoped：一次性建表/清库 ──────────────────────


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """建表 → 跑完全部测试 → drop 所有表和 schema"""
    async with test_engine.begin() as conn:
        schemas = {t.schema for t in Base.metadata.tables.values() if t.schema}
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        for schema in schemas:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        for schema in schemas:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        schemas = {t.schema for t in Base.metadata.tables.values() if t.schema}
        for schema in schemas:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))

    await test_engine.dispose()


# ── Function-scoped：直接会话（适用于仓储层单元测试）────


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """每个测试用例提供独立 AsyncSession。"""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.rollback()
        finally:
            await session.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """每个请求独立数据库会话的 httpx AsyncClient。

    httpx 是什么？
    ─────────────
    httpx 是 Python 的现代 HTTP 客户端库（类似 requests，但支持 async）。
    在测试中，它的杀手级功能是 ASGITransport：
      - 不需要启动真实的 uvicorn 服务器
      - 把 FastAPI app 直接挂载到 httpx 内部
      - 请求在同一个进程内完成（内存级别，极快）
      - 行为和真实 HTTP 请求完全一致（header、cookie、状态码）
    """
    app = await create_test_app()

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await _cleanup_test_app(app)


@pytest.fixture
async def authed_client(client: AsyncClient) -> AsyncClient:
    """已登录的 client（自动注册+登录，cookie 已设置）"""
    import uuid

    unique = uuid.uuid4().hex[:12]
    email = f"test_{unique}@test.com"
    password = "Test123456"
    device_id = str(uuid.uuid4())

    await client.post(
        "/v1/auth/register",
        json={"name": f"test_{unique}", "email": email, "password": password},
    )
    await client.post(
        "/v1/auth/login",
        json={"email": email, "password": password, "device_id": device_id},
    )
    return client
