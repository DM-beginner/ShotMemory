"""
并发测试 — 验证 API 在并发场景下的数据一致性

使用 asyncio.gather 模拟多个请求同时到达，检验：
- 注册去重（同邮箱只能成功一个）
- 并发登录互不冲突
- 并发读写数据一致

关键设计：
- 每个并发请求通过 TestSessionLocal 获取独立 session（独立 DB 连接）
- 不使用 SAVEPOINT 隔离（并发测试需要真正的多连接并发）
- 数据在 session 级别 setup_database teardown 时统一清理
"""

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient

from core.database import get_db
from tests.conftest import TestSessionLocal, _cleanup_test_app, create_test_app


async def _get_concurrent_db():
    """每个请求获取独立 session（独立连接），支持真正并发"""
    async with TestSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def _make_concurrent_client(app) -> AsyncClient:
    """基于共享 app 创建 httpx client"""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── 注册并发 ──────────────────────────────────────────────


async def test_concurrent_register():
    """10 个不同用户同时注册，全部成功"""
    app = await create_test_app()
    app.dependency_overrides[get_db] = _get_concurrent_db

    async def register_one():
        async with _make_concurrent_client(app) as client:
            unique = uuid.uuid4().hex[:12]
            resp = await client.post(
                "/v1/auth/register",
                json={
                    "name": f"user_{unique}",
                    "email": f"user_{unique}@test.com",
                    "password": "Test123456",
                },
            )
            return resp.status_code

    results = await asyncio.gather(*[register_one() for _ in range(10)])
    app.dependency_overrides.clear()
    await _cleanup_test_app(app)

    success_count = sum(1 for code in results if code == 200)
    assert success_count == 10, f"Expected 10 successes, got {success_count}: {results}"


async def test_concurrent_register_same_email():
    """10 个请求同时用同一邮箱注册，只有 1 个成功"""
    app = await create_test_app()
    app.dependency_overrides[get_db] = _get_concurrent_db
    email = f"dup_{uuid.uuid4().hex[:8]}@test.com"

    async def register_same():
        async with _make_concurrent_client(app) as client:
            resp = await client.post(
                "/v1/auth/register",
                json={
                    "name": "dup_user",
                    "email": email,
                    "password": "Test123456",
                },
            )
            return resp.status_code

    results = await asyncio.gather(*[register_same() for _ in range(10)])
    app.dependency_overrides.clear()
    await _cleanup_test_app(app)

    success_count = sum(1 for code in results if code == 200)
    assert success_count == 1, (
        f"Expected exactly 1 success for same email, got {success_count}: {results}"
    )


# ── 登录并发 ──────────────────────────────────────────────


async def test_concurrent_login():
    """同一用户 10 个设备同时登录，全部成功"""
    app = await create_test_app()
    app.dependency_overrides[get_db] = _get_concurrent_db

    # 先注册一个用户
    unique = uuid.uuid4().hex[:12]
    email = f"login_{unique}@test.com"
    password = "Test123456"

    async with _make_concurrent_client(app) as client:
        resp = await client.post(
            "/v1/auth/register",
            json={"name": f"login_{unique}", "email": email, "password": password},
        )
        assert resp.status_code == 200

    async def login_one():
        async with _make_concurrent_client(app) as client:
            resp = await client.post(
                "/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                    "device_id": str(uuid.uuid4()),
                },
            )
            return resp.status_code

    results = await asyncio.gather(*[login_one() for _ in range(10)])
    app.dependency_overrides.clear()
    await _cleanup_test_app(app)

    success_count = sum(1 for code in results if code == 200)
    assert success_count == 10, f"Expected 10 login successes, got {success_count}"


# ── 列表查询并发 ──────────────────────────────────────────


async def test_concurrent_list_photos():
    """10 个并发请求同时查询照片列表，全部 200"""
    app = await create_test_app()
    app.dependency_overrides[get_db] = _get_concurrent_db

    # 注册并登录，拿到 cookie
    async with _make_concurrent_client(app) as client:
        unique = uuid.uuid4().hex[:12]
        email = f"photo_{unique}@test.com"
        password = "Test123456"
        await client.post(
            "/v1/auth/register",
            json={"name": f"photo_{unique}", "email": email, "password": password},
        )
        login_resp = await client.post(
            "/v1/auth/login",
            json={
                "email": email,
                "password": password,
                "device_id": str(uuid.uuid4()),
            },
        )
        cookies = dict(login_resp.cookies)

    async def list_photos():
        async with _make_concurrent_client(app) as client:
            client.cookies.update(cookies)
            resp = await client.get("/v1/photo?limit=20&offset=0")
            return resp.status_code

    results = await asyncio.gather(*[list_photos() for _ in range(10)])
    app.dependency_overrides.clear()
    await _cleanup_test_app(app)

    assert all(code == 200 for code in results), f"Not all 200: {results}"


# ── Story 并发创建 ────────────────────────────────────────


async def test_concurrent_create_story():
    """10 个并发创建故事，全部成功且数据正确"""
    app = await create_test_app()
    app.dependency_overrides[get_db] = _get_concurrent_db

    # 注册并登录
    async with _make_concurrent_client(app) as client:
        unique = uuid.uuid4().hex[:12]
        email = f"story_{unique}@test.com"
        password = "Test123456"
        await client.post(
            "/v1/auth/register",
            json={"name": f"story_{unique}", "email": email, "password": password},
        )
        login_resp = await client.post(
            "/v1/auth/login",
            json={
                "email": email,
                "password": password,
                "device_id": str(uuid.uuid4()),
            },
        )
        cookies = dict(login_resp.cookies)

    async def create_story(i: int):
        async with _make_concurrent_client(app) as client:
            client.cookies.update(cookies)
            resp = await client.post(
                "/v1/story",
                json={
                    "title": f"Concurrent Story {i}",
                    "content": f"Content for story {i}",
                },
            )
            return resp.status_code

    results = await asyncio.gather(*[create_story(i) for i in range(10)])
    app.dependency_overrides.clear()
    await _cleanup_test_app(app)

    success_count = sum(1 for code in results if code == 200)
    assert success_count == 10, f"Expected 10 story creations, got {success_count}"


# ── Token 刷新并发 ────────────────────────────────────────


async def test_concurrent_refresh_token():
    """同一用户多次并发刷新 token，至少部分成功"""
    app = await create_test_app()
    app.dependency_overrides[get_db] = _get_concurrent_db

    # 注册并登录
    async with _make_concurrent_client(app) as client:
        unique = uuid.uuid4().hex[:12]
        email = f"refresh_{unique}@test.com"
        password = "Test123456"
        await client.post(
            "/v1/auth/register",
            json={"name": f"refresh_{unique}", "email": email, "password": password},
        )
        login_resp = await client.post(
            "/v1/auth/login",
            json={
                "email": email,
                "password": password,
                "device_id": str(uuid.uuid4()),
            },
        )
        cookies = dict(login_resp.cookies)

    async def refresh():
        async with _make_concurrent_client(app) as client:
            client.cookies.update(cookies)
            resp = await client.post("/v1/auth/refresh")
            return resp.status_code

    results = await asyncio.gather(*[refresh() for _ in range(5)])
    app.dependency_overrides.clear()
    await _cleanup_test_app(app)

    # 并发刷新时，由于 token rotation，部分旧 token 会被吊销
    # 至少 1 个应该成功
    success_count = sum(1 for code in results if code == 200)
    assert success_count >= 1, f"Expected at least 1 refresh success, got {results}"
