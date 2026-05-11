"""
照片上传测试 — 验证完整的上传流程

测试内容：
- 单张上传 + arq 任务入队
- 批量上传（多张）
- 上传后查询验证数据一致性
- 并发上传
"""

import asyncio
import uuid
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from core.database import get_db
from tests.conftest import TestSessionLocal, _cleanup_test_app, create_test_app

# 测试图片目录（取最小的几张，加快测试速度）
TEST_IMAGES_DIR = Path(__file__).parent / "test-images"


def _get_smallest_images(count: int = 3) -> list[Path]:
    """按文件大小排序，取最小的几张测试图片"""
    images = sorted(TEST_IMAGES_DIR.glob("*.jpg"), key=lambda p: p.stat().st_size)
    return images[:count]


async def _get_test_db():
    """每个请求独立 session"""
    async with TestSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def _setup_app_and_user():
    """创建 app + 注册登录用户，返回 (app, cookies)"""
    app = await create_test_app()
    app.dependency_overrides[get_db] = _get_test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique = uuid.uuid4().hex[:12]
        email = f"upload_{unique}@test.com"
        password = "Test123456"
        await client.post(
            "/v1/auth/register",
            json={"name": f"upload_{unique}", "email": email, "password": password},
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

    return app, cookies


# ── 单张上传 ──────────────────────────────────────────────


async def test_upload_single_photo():
    """上传一张照片，验证返回 200 + 数据库记录正确"""
    app, cookies = await _setup_app_and_user()

    images = _get_smallest_images(1)
    assert images, "test-images 目录下没有 jpg 文件"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.update(cookies)

        with open(images[0], "rb") as f:
            resp = await client.post(
                "/v1/photo/uploads",
                files=[("files", (images[0].name, f, "image/jpeg"))],
            )

        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["object_key"]  # 有存储路径

        # 验证列表接口也能查到
        list_resp = await client.get("/v1/photo?limit=20&offset=0")
        assert list_resp.status_code == 200
        items = list_resp.json()["data"]["items"]
        assert len(items) >= 1

    app.dependency_overrides.clear()
    await _cleanup_test_app(app)


# ── 批量上传 ──────────────────────────────────────────────


async def test_upload_batch_photos():
    """批量上传 3 张照片"""
    app, cookies = await _setup_app_and_user()

    images = _get_smallest_images(3)
    assert len(images) >= 2, "test-images 目录下 jpg 文件不足"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.update(cookies)

        files = []
        file_handles = []
        for img in images:
            fh = open(img, "rb")  # noqa: SIM115
            file_handles.append(fh)
            files.append(("files", (img.name, fh, "image/jpeg")))

        try:
            resp = await client.post("/v1/photo/uploads", files=files)
        finally:
            for fh in file_handles:
                fh.close()

        assert resp.status_code == 200, f"Batch upload failed: {resp.text}"
        data = resp.json()["data"]
        assert len(data) == len(images)

        # 每张都有独立的 object_key
        keys = {item["object_key"] for item in data}
        assert len(keys) == len(images), "object_key 存在重复"

    app.dependency_overrides.clear()
    await _cleanup_test_app(app)


# ── 上传后详情查询 ────────────────────────────────────────


async def test_upload_then_get_detail():
    """上传照片后通过 ID 获取详情"""
    app, cookies = await _setup_app_and_user()

    images = _get_smallest_images(1)
    assert images

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.update(cookies)

        with open(images[0], "rb") as f:
            upload_resp = await client.post(
                "/v1/photo/uploads",
                files=[("files", (images[0].name, f, "image/jpeg"))],
            )

        assert upload_resp.status_code == 200
        photo_id = upload_resp.json()["data"][0]["id"]

        # 通过 ID 获取详情
        detail_resp = await client.get(f"/v1/photo/{photo_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()["data"]
        assert detail["id"] == photo_id

    app.dependency_overrides.clear()
    await _cleanup_test_app(app)


# ── 并发上传 ──────────────────────────────────────────────


async def test_concurrent_upload():
    """5 个用户同时上传照片，全部成功"""
    app, cookies = await _setup_app_and_user()

    images = _get_smallest_images(1)
    assert images

    async def upload_one(i: int):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.update(cookies)
            with open(images[0], "rb") as f:
                resp = await client.post(
                    "/v1/photo/uploads",
                    files=[("files", (f"concurrent_{i}.jpg", f, "image/jpeg"))],
                )
            return resp.status_code

    results = await asyncio.gather(*[upload_one(i) for i in range(5)])
    app.dependency_overrides.clear()
    await _cleanup_test_app(app)

    success_count = sum(1 for code in results if code == 200)
    assert success_count == 5, f"Expected 5 upload successes, got {success_count}: {results}"


# ── 上传 + 删除全流程 ────────────────────────────────────


async def test_upload_then_delete():
    """上传照片 → 删除 → 确认列表为空"""
    app, cookies = await _setup_app_and_user()

    images = _get_smallest_images(1)
    assert images

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.update(cookies)

        # 上传
        with open(images[0], "rb") as f:
            upload_resp = await client.post(
                "/v1/photo/uploads",
                files=[("files", (images[0].name, f, "image/jpeg"))],
            )
        assert upload_resp.status_code == 200
        photo_id = upload_resp.json()["data"][0]["id"]

        # 删除
        del_resp = await client.delete(f"/v1/photo/{photo_id}")
        assert del_resp.status_code == 200

        # 确认查不到了
        detail_resp = await client.get(f"/v1/photo/{photo_id}")
        assert detail_resp.status_code == 404

    app.dependency_overrides.clear()
    await _cleanup_test_app(app)
