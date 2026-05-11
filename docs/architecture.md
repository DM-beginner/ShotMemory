# ShotMemory — 系统架构概览

## 1. 服务定位

ShotMemory 是一个全栈照片管理应用，由三类进程组成：

| 进程 | 职责 |
|------|------|
| **FastAPI 主服务** | HTTP API、认证、数据库读写、上传接收、任务投递（`backend/main.py`） |
| **arq Worker** | 后台 EXIF 解析、缩略图生成、动态视频转码、OSS 文件清理（`backend/core/worker.py`） |
| **前端 SPA** | React 19 + RTK Query，单一构建产物，通过 HTTPOnly Cookie 与后端通信 |

主服务和 Worker 共享同一份 SQLAlchemy 模型与 storage 抽象，但启动各自独立的数据库连接池与 Redis 队列连接，互不干扰。

---

## 2. 技术选型

| 层级 | 技术 |
|------|------|
| API 框架 | FastAPI（uvicorn + uvloop） |
| ORM | SQLAlchemy 2.x（DeclarativeBase / Mapped） |
| 数据校验 | Pydantic v2 |
| 业务数据库 | PostgreSQL 16 + PostGIS 3.4（asyncpg 驱动） |
| 任务队列 | arq + Redis 7（DB1） |
| 缓存 | Redis 7（DB0，物理隔离） |
| 图像 / 视频 | Pillow（缩略图）、pyexiftool（EXIF）、ffmpeg / ffprobe（视频转码） |
| 认证 | PyJWT + pwdlib（Argon2 推荐配置） |
| 对象存储 | 策略模式：`LocalStorageStrategy`（开发）/ `AliyunOSSStrategy`（生产，占位） |
| 序列化 | orjson |
| 依赖管理 | uv |
| 前端 | React 19 + Vite（rolldown-vite）+ Redux Toolkit / RTK Query + HeroUI + Tailwind CSS 4 |

---

## 3. 数据库全局规范

| 规范 | 说明 |
|------|------|
| 主键 | UUIDv7，`uuid6.uuid7` 作为 ORM 默认值，`gen_random_uuid()` 作为数据库 server 默认值。存储为原生 `UUID` 类型 |
| 外键 | 使用数据库层 FK，关键关系（`user_id` → `auth.user.id`、M2M）配 `ondelete=CASCADE` |
| Schema 划分 | `auth`、`photo_story`，每个领域独立 schema |
| 软删除 | `auth.user` 用 `is_deleted` 布尔字段；唯一索引为部分索引 `WHERE is_deleted = false`（释放邮箱/手机号） |
| 时间字段 | `created_at` / `updated_at` 通过 `CreatedTimeMixin` / `UpdatedTimeMixin` 注入，带时区，`server_default=func.now()` |
| 地理坐标 | 使用 PostGIS `Geometry(POINT, srid=4326)`（WGS84），WKT 格式写入，响应转 GeoJSON |
| 图片字段 | 数据库只存 `object_key`（OSS 相对路径），完整 URL 由前端拼接 |
| EXIF | `JSONB(none_as_null=True)` 存储；展平时按命名空间优先级合并（详见 `docs/modules/worker.md`） |
| 命名约定 | `core/base_model.py` 自定义 PostgreSQL 索引/约束命名（`%(column_0_label)s_idx` 等） |

---

## 4. 路由结构

所有业务路由统一前缀 `/v1`，由 `main.register_routes` 装配：

```
/                          # 根路径，重定向到 /docs
/docs                      # FastAPI 自带 Swagger UI
/static                    # 仅 ENV=dev 挂载，前端访问本地存储的图片/视频
/v1/
  auth/                    - 用户注册、登录、刷新、登出、注销、个人信息、头像
  photo/                   - 照片上传、查询、更新、删除（含批量删除）
  story/                   - 图文故事 CRUD
```

中间件由 `register_middleware` 装配：CORS（`settings.ORIGINS` 白名单 + `allow_credentials=True`）+ 请求日志中间件。

异常处理顺序（`register_exception_handlers`）：`BaseError` → `HTTPException` → `RequestValidationError` → `Exception`。

---

## 5. 数据库 ER 概览

### 5.1 用户体系（schema `auth`）

```
auth.user                       软删除：is_deleted 布尔
  │                             部分唯一索引（WHERE is_deleted = false）：
  │                               ix_user_name_active / ix_user_email_active / ix_user_phone_active
  │                             → 注销账号即释放邮箱/手机号/用户名供他人复用
  │
  └── auth.refresh_token        (one-to-many, ondelete=CASCADE, lazy="selectin")
        UNIQUE (user_id, device_id)   ← UPSERT 锚点：同设备复登覆盖、跨设备并存
        INDEX  (user_id, expires_at)  ← 清理过期 Token
        token_hash 仅存 SHA-256，即使拖库也无法伪造 JWT
```

字段定义见 `services/auth/models/`，迁移见 `alembic/versions/`。

### 5.2 照片与故事（schema `photo_story`）

```
photo_story.photo
  user_id (FK → auth.user.id, ondelete=CASCADE)
  object_key                      ← 原图 OSS 相对路径（缩略图/视频路径靠规则推导）
  has_video                       ← 是否存在配对/嵌入视频
  location_wkt (Geometry POINT 4326)  ← WGS84 GPS
  exif_data (JSONB)               ← 隐式状态机（详见 docs/modules/photo.md）
  taken_at / created_at
  INDEX (user_id), (object_key), (taken_at)

photo_story.story
  user_id (FK → auth.user.id, ondelete=CASCADE)
  cover_photo_id (FK → photo.id, ondelete=SET NULL)  ← 单独外键，非 M2M
  │
  └── photo_story.photo_story_m2m    (composite PK)
        story_id  (FK, ondelete=CASCADE)
        photo_id  (FK, ondelete=CASCADE)
        sort_order INT     ← 故事内照片显示顺序
```

字段定义见 `services/photo_story/models/`。`photo.exif_data` 是隐式状态机：`NULL` = 处理中，`{}` = 无 EXIF，`{...}` = 已完成；前端 `PhotoResponse.status` 是基于此的计算字段。

---

## 6. Redis 双库设计

`main.py` 的 lifespan 在启动时同时初始化两套连接池：

| 库 | URL 设置项 | 用途 | 客户端 |
|----|-----------|------|--------|
| **DB0** | `REDIS_CACHE_URL` | 通用缓存（应用层视情况使用） | `redis.asyncio.Redis.from_url(...)` |
| **DB1** | `REDIS_ARQ_URL`   | arq 任务队列 | `arq.create_pool(RedisSettings.from_dsn(...))` |

物理隔离的核心目的：缓存高并发不能拖垮任务队列，反之亦然。两者通过 `app.state.redis_cache` / `app.state.arq_queue` 暴露，并经由依赖注入：

- 路由通过 `RedisDep`（`Annotated[ArqRedis, Depends(get_redis)]`）使用任务队列
- `get_redis_cache` 依赖暴露缓存 Redis

Worker 进程不持有这两个连接池——它通过 `arq core.worker.WorkerSettings` 启动时由 arq 自己持有 Redis DB1 连接。

---

## 7. 存储策略

策略模式 `core/storage/interface.StorageStrategy` 抽象出四个方法：

```
upload_file(file: UploadFile)         → 原图直存 originals/
upload_bytes(data, suffix, subdir)    → 字节流（缩略图、转码后视频）
download_to_file(object_key)          → Worker 取本地 Path
delete_file(object_key)               → 删除
```

`get_storage_service()`（`core/storage/__init__.py`）使用 `lru_cache` 单例，按 `ENV` 切换：

- `dev` → `LocalStorageStrategy(upload_dir, base_url)`，原图、缩略图、视频分别落到 `uploads/originals/`、`uploads/thumbnails/`、`uploads/videos/`，FastAPI `StaticFiles` 挂载 `/static`
- `prod` → `AliyunOSSStrategy`（**当前为占位实现**，所有方法 `raise NotImplementedError`，详见 `docs/production-readiness.md`）

**`object_key` 派生规则**（`derive_thumbnail_key` / `derive_video_key`，定义在 `services/photo_story/schemas/photo_schema.py`）：

| 衍生文件 | 规则 |
|----------|------|
| 缩略图 | `uploads/originals/abc.heic` → `uploads/thumbnails/abc.webp` |
| 视频   | `uploads/originals/abc.heic` → `uploads/videos/abc.mp4` |

数据库只存原图 `object_key`，缩略图与视频路径由 `derive_thumbnail_key` / `derive_video_key` 在响应序列化时计算。

详见 [`docs/modules/storage.md`](./modules/storage.md)。

---

## 8. 认证与 Cookie 策略

### 双 Token 模型

| Token | 有效期 | Cookie 路径 | 用途 |
|-------|--------|-------------|------|
| `access_token`  | 30 分钟 | `/`        | 访问业务接口 |
| `refresh_token` | 7 天    | `/v1/auth` | 仅在 `/v1/auth/*` 下回传，缩小泄露面 |

两个 Cookie 均为 `HTTPOnly`，配置 `Secure`（生产）+ `SameSite=lax` + 可选 `domain`（`settings.COOKIE_*`）。

### Refresh Token UPSERT

`refresh_token` 表以 `(user_id, device_id)` 为唯一约束。`RefreshTokenRepo.upsert_refresh_token` 用一条 PostgreSQL CTE 同时完成两件事：

1. `INSERT ... ON CONFLICT (user_id, device_id) DO UPDATE SET token_hash, expires_at`
2. `UPDATE auth.user SET last_active_at = NOW()`

效果：同设备复登覆盖旧 token；不同设备并存；同时刷新用户 `last_active_at`，避免两次往返。完整 SQL 见 repo 实现。

### 设备语义

`device_id` 由前端通过 `crypto.randomUUID()` 生成并持久化到 `localStorage` 键 `shotmemory_device_id`。最新迁移 `2026_04_20_1648` 移除了 `device_id` 全局唯一约束，允许多用户共享同一台设备。

### 密码

`pwdlib.PasswordHash.recommended()` —— 当前实际使用 Argon2id（README 注释中误写"bcrypt"）。

详见 [`docs/modules/auth.md`](./modules/auth.md)。

---

## 9. 依赖注入别名

| 别名 | 类型 | 来源文件 |
|------|------|---------|
| `SessionDep` | `Annotated[AsyncSession, Depends(get_db)]` | `core/database.py` |
| `RedisDep` | `Annotated[ArqRedis, Depends(get_redis)]` | `core/database.py` |
| `StorageDep` | `Annotated[StorageStrategy, Depends(get_storage_service)]` | `core/storage/__init__.py` |
| `CurrentUser` | `Annotated[User, Depends(get_current_user)]` | `services/auth/routers/user_deps.py` |
| `TokenDep` | `Annotated[str, Depends(get_token_from_request)]` | 同上 |

`get_current_user` 优先从 `Authorization: Bearer ...` 读取（Swagger UI 友好），回退到 `access_token` Cookie（前端实际路径）。

---

## 10. 异步任务

`core/worker.py` 注册到 `WorkerSettings.functions`：

| 任务 | 触发时机 | 执行内容 | 重试 |
|------|---------|---------|------|
| `parse_photo_exif(photo_id, object_key, pre_video_key)` | 照片上传成功后 enqueue | EXIF 解析 + 缩略图生成 + 动态视频提取/转码 + 单事务 UPDATE | `max_tries=3` |
| `delete_oss_files(keys)` | 单/批量删除照片后 enqueue | 并发 `delete_file`，统计失败数；有失败抛错以触发 arq 重试 | `max_tries=3` |

并发约束：

- `WorkerSettings.max_jobs = 10`
- `_heavy_sem = asyncio.Semaphore(WORKER_MAX_HEAVY_TASKS)`（默认 3，防止 Pillow + ffmpeg 同时挤爆 CPU/内存）
- `WorkerSettings.job_timeout = 120` 秒

详见 [`docs/modules/worker.md`](./modules/worker.md)。

---

## 11. 统一响应

`core/unify_response.UnifyResponse` 使用 orjson 直接渲染：

```json
{ "code": 20000, "message": "操作成功", "data": <T | null> }
```

| 类方法 | HTTP 状态 | 用途 |
|--------|-----------|------|
| `UnifyResponse.success(data, message, code)` | 200 | 业务成功 |
| `UnifyResponse.frontend_error(code, message, data, status_code=400)` | 400+（默认） | 客户端错误 |
| `UnifyResponse.backend_error(code, message, data, status_code=500)` | 500+ | 服务端错误 |

业务状态码集中在 `core/exceptions.APIStatus`：

| 段位 | 含义 | 示例 |
|------|------|------|
| `20000` | 成功 | `SUCCESS` |
| `400xx` | 通用客户端错误 | `BAD_REQUEST(40000)`、`UNAUTHORIZED(40001)` |
| `401xx` | 用户/认证 | `USER_PASSWORD_ERROR(40102)`、`USER_EXISTS(40103)` |
| `402xx` | Token | `TOKEN_INVALID(40201)`、`TOKEN_EXPIRED(40203)` |
| `403xx` | 文件/存储 | `FILE_TYPE_NOT_ALLOWED(40304)`、`FILE_TOO_LARGE(40305)` |
| `404xx` | 照片/故事 | `PHOTO_NOT_FOUND(40401)`、`STORY_NOT_FOUND(40404)` |
| `500xx` | 服务端 | `SYSTEM_ERROR(50000)`、`DB_ERROR(50001)` |

抛 `BaseError(code, message, data, status_code)` 即可由全局 handler 转成上述格式。

---

## 12. 数据库连接池细节

`core/database.py` 主服务引擎：

| 配置 | 值 | 说明 |
|------|----|------|
| `pool_pre_ping` | True | 取连接时先 SELECT 1 验活 |
| `pool_recycle` | 3600 | 一小时回收，规避数据库主动断连 |
| `pool_size` | 50 | 主服务常驻连接数 |
| `max_overflow` | 20 | 峰值额外连接（合计 70） |
| `pool_timeout` | 10 s | 取连接超时，快速失败 |
| `expire_on_commit` | False | commit 后属性不过期，避免触发额外 SELECT |
| 每会话首条 SQL | `SET statement_timeout = 5000` | 防止慢查询打死池 |

Worker 进程使用独立小池（`pool_size=5, max_overflow=5`），仅在回写阶段持有连接。

---

## 13. 测试

后端使用独立的 `shotmemory_test` 库（`db-init/init-test-db.sql`）。`backend/tests/conftest.py` 设计要点：

- session 级 fixture 一次性建表 / 测完 drop schema
- 每个 HTTP 用例使用独立 `AsyncClient` + 独立 `AsyncSession`
- 真实连接 Redis（不 mock），arq 任务真实入队
- `authed_client` fixture 自动注册 + 登录，cookie 已就绪

测试文件位置：`backend/tests/{test_uploads.py,test_concurrent.py,locustfile.py}`。

> 测试夹具图片在 `backend/tests/test-images/` 下，约 500 MB，**不入 git**（已在 `.gitignore` 排除），首次 clone 后需手动放置——详见 `backend/tests/README.md`。

---

## 14. 关键设计决策

ADR 速览另见 [`docs/decisions.md`](./decisions.md)。该文档集中解释"为什么是这样而不是那样"——任务队列选 arq、Redis 物理分库、HTTPOnly Cookie、部分唯一索引、device_id 由前端生成、存储策略模式、派生路径规则推导、上传 All-or-Nothing、缩略图条件返回、删除走 OSS 异步清理。
