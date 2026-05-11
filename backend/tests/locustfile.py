"""
ShotMemory 并发性能测试

基于 Locust 框架，模拟真实用户行为对 FastAPI 后端进行压力测试。
覆盖 Auth、Photo、Story 三大业务域。

运行方式:
    # Web UI 模式
    uv run locust -f tests/locustfile.py --host=http://localhost:5683

    # 无头模式
    uv run locust -f tests/locustfile.py --host=http://localhost:5683 \
        --headless -u 100 -r 10 --run-time 60s
"""

import random
import uuid
from pathlib import Path

from locust import HttpUser, between, task

# 取 test-images 目录中最小的一张作为上传样本
_TEST_IMAGES_DIR = Path(__file__).parent / "test-images"
_candidates = sorted(_TEST_IMAGES_DIR.glob("*.jpg"), key=lambda p: p.stat().st_size)
SAMPLE_IMAGE = _candidates[0] if _candidates else _TEST_IMAGES_DIR / "sample.jpg"


class ShotMemoryUser(HttpUser):
    """模拟真实用户行为的虚拟用户"""

    wait_time = between(1, 3)

    # 缓存已获取的资源 ID，用于详情接口联动
    photo_ids: list[str]
    story_ids: list[str]

    def on_start(self):
        """每个虚拟用户启动时自动注册 + 登录"""
        self.photo_ids = []
        self.story_ids = []

        unique = uuid.uuid4().hex[:12]
        self.email = f"locust_{unique}@test.com"
        self.password = "Test123456"
        self.device_id = str(uuid.uuid4())

        # 注册
        self.client.post(
            "/v1/auth/register",
            json={
                "name": f"locust_{unique}",
                "email": self.email,
                "password": self.password,
            },
        )

        # 登录（Cookie 由 HttpUser 自动管理）
        self.client.post(
            "/v1/auth/login",
            json={
                "email": self.email,
                "password": self.password,
                "device_id": self.device_id,
            },
        )

    # ── Auth 域 ──────────────────────────────────────────────

    @task(2)
    def get_me(self):
        """获取当前用户信息"""
        self.client.get("/v1/auth/me")

    @task(1)
    def refresh_token(self):
        """刷新 Token"""
        self.client.post("/v1/auth/refresh")

    # ── Photo 域 ─────────────────────────────────────────────

    @task(5)
    def list_photos(self):
        """浏览照片列表（随机分页）"""
        offset = random.randint(0, 5) * 25
        with self.client.get(
            f"/v1/photo?limit=25&offset={offset}",
            name="/v1/photo?limit=25",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                items = data.get("items", [])
                for item in items:
                    if item.get("id") and item["id"] not in self.photo_ids:
                        self.photo_ids.append(item["id"])
                # 只保留最近 50 个，避免内存无限增长
                self.photo_ids = self.photo_ids[-50:]
                resp.success()

    @task(3)
    def get_photo_detail(self):
        """查看照片详情"""
        if not self.photo_ids:
            return
        photo_id = random.choice(self.photo_ids)
        self.client.get(f"/v1/photo/{photo_id}", name="/v1/photo/[id]")

    @task(1)
    def upload_photo(self):
        """上传照片"""
        if not SAMPLE_IMAGE.exists():
            return
        with open(SAMPLE_IMAGE, "rb") as f:
            self.client.post(
                "/v1/photo/uploads",
                files=[("files", ("sample.jpg", f, "image/jpeg"))],
                name="/v1/photo/uploads",
            )

    # ── Story 域 ─────────────────────────────────────────────

    @task(3)
    def list_stories(self):
        """浏览故事列表"""
        with self.client.get(
            "/v1/story?limit=20&offset=0",
            name="/v1/story?limit=20",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                items = data.get("items", [])
                for item in items:
                    if item.get("id") and item["id"] not in self.story_ids:
                        self.story_ids.append(item["id"])
                self.story_ids = self.story_ids[-50:]
                resp.success()

    @task(2)
    def get_story_detail(self):
        """查看故事详情"""
        if not self.story_ids:
            return
        story_id = random.choice(self.story_ids)
        self.client.get(f"/v1/story/{story_id}", name="/v1/story/[id]")

    @task(1)
    def create_story(self):
        """创建故事"""
        unique = uuid.uuid4().hex[:8]
        payload: dict = {
            "title": f"Locust 测试故事 {unique}",
            "content": f"这是一个由 Locust 压测创建的故事 {unique}",
        }
        # 如果有照片 ID，随机关联 1~3 张
        if self.photo_ids:
            count = min(random.randint(1, 3), len(self.photo_ids))
            payload["photo_ids"] = random.sample(self.photo_ids, count)

        with self.client.post(
            "/v1/story", json=payload, catch_response=True, name="/v1/story [create]"
        ) as resp:
            if resp.status_code == 200:
                story_id = resp.json().get("data", {}).get("id")
                if story_id and story_id not in self.story_ids:
                    self.story_ids.append(story_id)
                resp.success()

    @task(1)
    def update_story(self):
        """更新故事"""
        if not self.story_ids:
            return
        story_id = random.choice(self.story_ids)
        unique = uuid.uuid4().hex[:8]
        self.client.patch(
            f"/v1/story/{story_id}",
            json={"title": f"Updated 故事 {unique}"},
            name="/v1/story/[id] [update]",
        )

    @task(1)
    def delete_story(self):
        """删除故事（低频）"""
        if not self.story_ids:
            return
        story_id = self.story_ids.pop(random.randrange(len(self.story_ids)))
        self.client.delete(
            f"/v1/story/{story_id}", name="/v1/story/[id] [delete]"
        )

    @task(1)
    def delete_photo(self):
        """删除照片（低频）"""
        if not self.photo_ids:
            return
        photo_id = self.photo_ids.pop(random.randrange(len(self.photo_ids)))
        self.client.delete(
            f"/v1/photo/{photo_id}", name="/v1/photo/[id] [delete]"
        )

    @task(1)
    def batch_delete_photos(self):
        """批量删除照片"""
        if len(self.photo_ids) < 2:
            return
        count = min(random.randint(2, 5), len(self.photo_ids))
        to_delete = [self.photo_ids.pop(random.randrange(len(self.photo_ids))) for _ in range(count)]
        self.client.post(
            "/v1/photo/batch-delete",
            json={"photo_ids": to_delete},
            name="/v1/photo/batch-delete",
        )

    @task(2)
    def list_photos_large_offset(self):
        """大分页偏移量（边界场景）"""
        offset = random.randint(50, 200) * 25
        self.client.get(
            f"/v1/photo?limit=25&offset={offset}",
            name="/v1/photo?limit=25 [large offset]",
        )
