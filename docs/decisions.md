# 关键设计决策（ADR 速览）

把散落在各模块"业务规则"里的决策集中在这里，方便回看"当时为什么这么选"。每条遵循：**背景 → 选择 → 主要替代 → 当前状态**。

---

## D-01 任务队列：arq

- **背景**：需要把 EXIF 解析、缩略图生成、ffmpeg 转码这些 CPU 密集任务从 HTTP 请求路径剥离。
- **选择**：arq（Redis-based，async 原生）。
- **主要替代**：Celery（更成熟生态，支持 broker 多样化）；RQ（同步设计）；FastAPI BackgroundTasks（生命周期跟随请求，不适合长任务）。
- **当前状态**：稳定。`WorkerSettings.functions` 单文件注册，启动一行命令；与 FastAPI 共享 SQLAlchemy 模型；`max_tries=3` 失败重试；和 `_heavy_sem` 信号量配合控制 CPU 并发。Celery 的更复杂运维成本对当前规模不必要。

## D-02 Redis 物理分库：DB0 缓存 / DB1 队列

- **背景**：缓存读写和任务队列写入若共用同一逻辑库，高并发场景下互相挤占连接和命令通道。
- **选择**：物理分库——`REDIS_CACHE_URL`（DB0）+ `REDIS_ARQ_URL`（DB1），两套独立连接池。
- **主要替代**：单库共用（key prefix 区分）；上独立 Redis 实例（成本翻倍）。
- **当前状态**：分库已落地，主服务 lifespan 同时初始化两套，依赖注入用 `RedisDep`（队列）/ `get_redis_cache`（缓存）区分。

## D-03 认证：HTTPOnly Cookie 而非 Authorization Header

- **背景**：前端是 SPA，需要"刷新页面后保持登录" + "防止 XSS 偷 token"。
- **选择**：access + refresh 都用 HTTPOnly Cookie 下发；前端不可访问 token，浏览器自动携带。
- **主要替代**：`Authorization: Bearer ...` Header + `localStorage`（XSS 风险高）；Header + 内存（页面刷新即失效，UX 差）。
- **当前状态**：稳定。`access_token` cookie path `/`，`refresh_token` path `/v1/auth`（缩小泄露面）。Swagger UI 仍接受 `Authorization: Bearer ...` 作为 fallback，方便调试。

## D-04 软删除：PostgreSQL 部分唯一索引

- **背景**：用户软删除后，邮箱/手机号要能被新账号复用，但又不能让活跃账号撞车。
- **选择**：所有"释放性"唯一约束都用部分索引 `WHERE is_deleted = false`（`ix_user_email_active` 等）。
- **主要替代**：普通 UNIQUE + 软删时把字段加后缀（如 `email = "old@x.com_deleted_<id>"`，丑且容易撞名）；业务层判重（并发安全难保证）。
- **当前状态**：稳定。注销账号立即释放唯一性，无需后台清理任务。**陷阱**：未来加新唯一字段时不要顺手写普通 UNIQUE。

## D-05 设备绑定：前端生成 `device_id`

- **背景**：要支持"同一用户多设备并存"且"同设备复登覆盖旧 token"。
- **选择**：前端 `crypto.randomUUID()` 生成 UUID，写入 `localStorage["shotmemory_device_id"]`，登录请求体回传；后端以 `(user_id, device_id)` 作为 refresh_token 表的 UPSERT 锚点。
- **主要替代**：后端用 IP / UA / 浏览器 fingerprint 推算（不稳定，浏览器换皮即变）；登录时返回 device_id 让前端记（多了一次往返且安全性等价）。
- **当前状态**：稳定。`device_id` 全局唯一约束在 `2026_04_20_1648` 迁移中被移除（允许多用户共享一台设备），现在只是 `(user_id, device_id)` 复合唯一。

## D-06 存储抽象：策略模式而非配置开关

- **背景**：开发环境用本地文件、生产环境用 OSS，两套 API 形态差异大（流式 vs 字节、本地 path vs HTTP）。
- **选择**：`StorageStrategy` 抽象基类 + `LocalStorageStrategy` / `AliyunOSSStrategy`，`get_storage_service()` 按 `ENV` lru_cache 单例返回。
- **主要替代**：在每个调用点 `if env == "dev": ... else: ...`（散乱、难测试）；只支持 OSS（开发环境强依赖云资源，本地起服务麻烦）。
- **当前状态**：interface 稳定，本地实现完整，OSS 实现**仍是占位**（`raise NotImplementedError`）。详见 `docs/production-readiness.md`。

## D-07 派生路径：规则推导而非数据库冗余字段

- **背景**：每张照片可能有原图 + 缩略图 + 视频共 3 个 OSS path，落库 3 个字段会产生不一致风险。
- **选择**：DB 只存 `object_key`（原图）；`derive_thumbnail_key` / `derive_video_key` 用文件名 stem 即时推导。
- **主要替代**：3 个字段都落库（写一致性需要 worker 里多步事务）；客户端推导（每个客户端重复实现，易漂移）。
- **当前状态**：稳定。条件返回控制：`thumbnail_key` 仅在 `exif_data is not None` 时返回（避免 404），`video_key` 仅在 `has_video=true` 时返回。

## D-08 上传校验：All-or-Nothing

- **背景**：批量上传若部分成功部分失败，前端要做复杂的"哪些成功哪些没成"展示，且数据库可能有半成功状态。
- **选择**：任一文件不合规（类型/大小/数量）直接 400 拒绝整批；上传过程中崩溃则按 `uploaded_keys` 反向清理已落盘的文件。
- **主要替代**：部分成功 + 返回每张状态（实现复杂，前端 UX 也复杂）。
- **当前状态**：稳定。代价是用户体验上"一颗老鼠屎坏一锅粥"，但对照片管理这种单次小批量场景可接受。

## D-09 缩略图：仅在处理结束后返回，不给占位 URL

- **背景**：上传后 worker 还在跑时，前端如果直接拼缩略图 URL 会得到 404。
- **选择**：`thumbnail_key` 仅在 `exif_data is not None`（即 worker 处理结束）时由 `PhotoResponse` 计算返回；之前是 `null`，前端按 `status="processing"` 渲染占位。
- **主要替代**：永远返回 URL，前端处理 404（污染日志、错误统计噪音）；返回 base64 占位（响应体膨胀）。
- **当前状态**：稳定。`status` 状态机契约保证 worker 必让 `exif_data` 翻成"非 null"。

## D-10 删除照片：DB 同步删除 + OSS 异步清理

- **背景**：删除时 OSS 失败（网络抖动、限流）若让 DB 也跟着失败，前端要等很久还可能撞 timeout。
- **选择**：路由层 DB 同步短事务删记录立即返回；OSS 清理通过 arq `delete_oss_files` 异步执行，失败计数 > 0 自动重试整批（`max_tries=3`）。
- **主要替代**：DB + OSS 在同一事务（不可能，OSS 不支持事务）；删除标记软删 + 后台 GC（多了一份"已删但仍在 OSS"的中间态，复杂）。
- **当前状态**：稳定。前端不会感知 OSS 失败；越权拦截在 `get_keys_for_deletion` 一条 SQL 里完成（防 UUID 枚举攻击）。
