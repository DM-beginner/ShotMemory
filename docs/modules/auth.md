# 用户与认证模块

## 1. 概述

`backend/services/auth/` 负责：

- 用户注册（邮箱或手机号二选一）
- 登录与双 Token 颁发（access + refresh，HTTPOnly Cookie）
- 设备感知的 Refresh Token 轮转（UPSERT 锚点：`(user_id, device_id)`）
- Token 静默刷新、登出、账号注销（软删除）
- 当前用户信息 / 头像上传

依赖：`core.security`（JWT + Argon2）、`core.unify_response`、`core.storage`、`services.photo_story.utils.image_util`（用于头像缩略图）。

## 2. 认证主线 TLDR

- JWT 通过 **HTTPOnly Cookie** 下发，不是 `Authorization` Header；前端不持有 token，靠浏览器自动携带。
- 双 Token：`access_token`（30 分钟，path `/`）+ `refresh_token`（7 天，path `/v1/auth`，仅在 `/v1/auth/*` 下回传以缩小泄露面）。
- 刷新流程是**设备感知的 UPSERT**：前端用 `crypto.randomUUID()` 生成 `device_id` 持久化到 `localStorage["shotmemory_device_id"]`，登录时随请求体上送；后端以 `(user_id, device_id)` 为冲突锚点 UPSERT，同设备复登覆盖、跨设备并存。
- 前端 RTK Query 的 `baseQueryWithReauth` 在 `401 + message=="Token expired"` 时自动调 `/v1/auth/refresh` 重试原请求；其他 401 直接退到登录态。

---

## 3. 数据模型

> **通用规范**：主键 UUIDv7，时间字段带时区，详见 `docs/architecture.md` § 3。字段定义以 `services/auth/models/` 为准；下表只列**非显然**字段或带特殊语义的字段。

### 3.1 `auth.user`

| 字段 | 类型 | 说明 |
|------|------|------|
| email | VARCHAR(255) NULL | 部分唯一索引 `WHERE is_deleted = false` |
| phone | VARCHAR(20) NULL | 同上 |
| name | VARCHAR(50) | 同上（用户名/昵称也走部分唯一） |
| avatar_key | VARCHAR(255) NULL | OSS path（不含域名） |
| hashed_password | VARCHAR | Argon2id（pwdlib 推荐配置） |
| is_deleted | BOOL | 软删除；置 true 后部分唯一索引立即释放邮箱/手机号供他人复用 |
| last_active_at | TIMESTAMPTZ | 登录/刷新时由 CTE 同步更新 |

### 3.2 `auth.refresh_token`

| 字段 | 类型 | 说明 |
|------|------|------|
| token_hash | VARCHAR(255) UNIQUE | refresh_token 的 SHA-256 哈希；只存哈希，即使拖库也无法伪造 JWT |
| expires_at | TIMESTAMPTZ | now + `REFRESH_TOKEN_EXPIRE_DAYS` |
| device_id | UUID INDEX | 前端生成的设备 UUID（非全局唯一，允许多用户共享一台设备） |

约束与索引：

```
UNIQUE (user_id, device_id)    ← UPSERT 锚点
INDEX  (user_id, expires_at)   ← 清理过期 Token
INDEX  (device_id)             ← 单字段查询
```

> `device_id` 全局唯一约束在迁移 `2026_04_20_1648_allow_device_id_reuse_across_users` 中被移除——所以是 INDEX 而非 UNIQUE。

---

## 4. API 接口

所有接口前缀 `/v1/auth`。完整请求/响应字段见 `/v1/docs`（FastAPI 自动生成的 OpenAPI），以下只列**非显然**的请求语义。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/register` | POST | 注册。`email` 与 `phone` 至少传一个（Pydantic `model_validator`）；password 6-128；中国大陆手机号校验 `^1[3-9]\d{9}$` |
| `/auth/login` | POST | 登录。请求体 `device_id` **必传**；写入两个 HTTPOnly Cookie；CTE UPSERT token + UPDATE `last_active_at` |
| `/auth/token` | POST | OAuth2 标准端点（`application/x-www-form-urlencoded`），仅供 Swagger UI / 命令行测试；`username` 含 `@` 视为邮箱、否则手机号；`device_id` 由后端随机生成 |
| `/auth/refresh` | POST | 无请求体；`refresh_token` 从 Cookie 读取；解码后必须 `type=="refresh"`；过期则同步删除该记录；复用 `db_token.device_id` 作为 UPSERT 锚点 |
| `/auth/logout` | POST | 删 DB 中对应 refresh token，无论成败都清两个 Cookie |
| `/auth/account` | DELETE | 软删除当前用户（`is_deleted=true`）；删该用户**所有** refresh token；清 Cookie。借助部分唯一索引，原邮箱/手机号立即可被他人注册复用 |
| `/auth/me` | GET | 需有效 access_token |
| `/auth/avatar` | PUT | `multipart/form-data`，字段 `file`；允许 `image/jpeg | png | webp | heic | heif | avif`，最大 50 MB；自动生成 200px WebP 缩略图，旧头像自动删除 |

错误码段位见 `docs/architecture.md` § 11。常用：`USER_EXISTS(40103)`、`USER_PASSWORD_ERROR(40102)`、`TOKEN_EXPIRED(40203)`、`FILE_TYPE_NOT_ALLOWED(40304)`。

---

## 5. 业务规则

1. **邮箱 / 手机号必须且只须一项可用**：注册和登录的请求模型都通过 Pydantic `model_validator` 校验"至少传一个"。
2. **密码哈希**：`pwd_context = PasswordHash.recommended()`（pwdlib 推荐，当前为 Argon2id）。注册时哈希后入库；登录时 `verify_password`。
3. **JWT Payload**（`core/security.create_token`）：
   ```json
   { "sub": "<user_uuid>", "type": "access" | "refresh", "exp": <ts>, "iat": <ts>, "jti": "<uuid4>" }
   ```
4. **Token 来源回退**（`user_deps.get_token_from_request`）：先 `Authorization: Bearer ...`（Swagger UI 友好），再 `access_token` Cookie（前端实际路径）。
5. **Token 类型校验**：`get_current_user` 必须看到 `type == "access"`，否则 401。`/auth/refresh` 必须看到 `type == "refresh"`。
6. **设备语义**：`device_id` 是同一用户多端登录的唯一区分键。同设备复登 → 覆盖；不同设备 → 并存。
7. **CTE UPSERT**（`RefreshTokenRepo.upsert_refresh_token`）：单条 SQL 同时 `INSERT ... ON CONFLICT (user_id, device_id) DO UPDATE` 并 `UPDATE auth.user SET last_active_at = NOW()`，避免两次往返。
8. **软删除唯一性陷阱**：所有"释放性"唯一约束都用 PostgreSQL 部分索引；不要把 email/phone/name 写成普通 UNIQUE。
9. **过期 Token 自清理**：`/auth/refresh` 命中过期 token 时立即删除该记录；`RefreshTokenRepo.clean_expired_tokens` 提供给定时任务做兜底批清。
10. **Token 仅存哈希**：`token_hash = SHA-256(refresh_token)`（`TokenUtil.make_hash_token`），即使数据库泄露，无法伪造 JWT。
11. **错误响应**：`AuthError` / `UserError` / `TokenError` 继承 `BaseError`，由全局 `business_error_handler` 统一转 `UnifyResponse`。

---

## 6. 依赖关系

| 依赖于 | 用途 |
|--------|------|
| `core.security` | JWT 签发 / 校验、Argon2 |
| `core.unify_response` | 响应序列化 |
| `core.storage` | 头像上传/删除 |
| `services.photo_story.utils.image_util` | 头像缩略图（200px WebP） |

| 被依赖 | 用途 |
|--------|------|
| `services.photo_story.routers.photo_router` | `CurrentUser` 依赖项 |
| `services.photo_story.routers.story_router` | `CurrentUser` 依赖项 |
| 任何未来加入的业务模块 | `CurrentUser` 是全局认证入口 |

---

## 7. 关键源码索引

代码位置：`backend/services/auth/`。子目录：`models/`、`repos/`、`routers/`、`schemas/`、`utils/`、`exceptions.py`。Cookie 设置统一在 `auth_router._set_auth_cookies`；UPSERT 在 `RefreshTokenRepo.upsert_refresh_token`；`CurrentUser` 在 `routers/user_deps`。
