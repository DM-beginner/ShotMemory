# 术语表

项目内有特殊语义的词汇，跨模块讨论时统一口径。

| 术语 | 含义 |
|------|------|
| `object_key` | 数据库持久化的相对路径，POSIX 风格，**不含域名**。如 `uploads/originals/abc.heic`。前端拼 URL 用 `${VITE_STORAGE_BASE_URL}/${object_key}`。 |
| `device_id` | 前端 `crypto.randomUUID()` 生成的 UUID，写入 `localStorage["shotmemory_device_id"]`。登录请求体必传，作为 refresh_token 表 `(user_id, device_id)` UPSERT 的锚点。允许多用户共享一台设备。 |
| `ContentIdentifier` | Apple Live Photo 的 QuickTime 元数据 UUID。用于把同批 HEIC 与 MOV 配对成一个 Live Photo（`ImageUtil.extract_content_identifier`）。 |
| Motion Photo | Android 厂商（Google / Samsung / OPPO）的"动态照片"格式，视频嵌入在 JPEG/HEIC 文件末尾，靠 EXIF 中 `MotionPhotoOffset` / `MicroVideoOffset` 或 `ftyp` box 偏移定位。 |
| Live Photo | iOS 的"动态照片"格式，HEIC + 同名 MOV 两个文件，靠 `ContentIdentifier` 配对。 |
| `has_video` | photo 表布尔字段，由 worker 根据上述两类视频是否提取/转码成功决定。响应里 `video_key` 仅在 `has_video=true` 时返回。 |
| `status`（PhotoResponse）| 计算字段，**不落库**。三态：`processing` / `completed` / `no_exif`。由 `exif_data` 状态机驱动。 |
| `exif_data` 三态 | `null` = worker 未完成（前端继续轮询）；`{}` = 处理完成但无 EXIF；`{...}` = 处理完成（可能含 `_error` 键表示局部失败）。**Worker 必把它从 null 翻成"非 null"**——这是核心契约。 |
| `pre_video_key` | iOS Live Photo 上传时记录的"待转码 MOV"路径（如 `uploads/videos/abc.mov`），传给 worker 的 `parse_photo_exif` 任务。worker 转码成 MP4 后会删除这个 MOV。 |
| `_heavy_sem` | Worker 进程内的 `asyncio.Semaphore(WORKER_MAX_HEAVY_TASKS)`，默认 3。包裹 Pillow 缩略图 + ffmpeg 转码两类重计算，防止 `max_jobs=10` 个任务并行烧掉 CPU/内存。 |
| `derive_thumbnail_key` / `derive_video_key` | `services/photo_story/schemas/photo_schema` 中的派生函数，把原图 `object_key` 推导成对应缩略图 / 视频路径。DB 不存这两个字段。 |
| `SessionDep` / `RedisDep` / `StorageDep` / `CurrentUser` | FastAPI 路由签名常用的 4 个依赖注入别名。详见 `docs/architecture.md` § 9。 |
| `UnifyResponse` | 统一响应封装，`{ "code": 20000, "message": "...", "data": <T \| null> }`。三个工厂方法：`success` / `frontend_error` / `backend_error`。 |
| `BaseError` | 业务异常基类，签名 `BaseError(code, message, data, status_code)`。全局 handler 会把它转成 `UnifyResponse`。 |
| `APIStatus` | 业务状态码枚举（`core/exceptions`），按段位划分：`200xx` 成功 / `400xx` 通用客户端 / `401xx` 用户认证 / `402xx` Token / `403xx` 文件存储 / `404xx` 照片故事 / `500xx` 服务端。 |
| All-or-Nothing | 上传校验策略：任一文件不合规（类型/大小/数量超限）→ 400 拒绝整批，绝不半成功。 |
| 部分唯一索引 | PostgreSQL `CREATE UNIQUE INDEX ... WHERE is_deleted = false`，让软删除账号释放邮箱/手机号供他人复用。 |
| CTE UPSERT | refresh_token 刷新用的 PostgreSQL CTE：一条 SQL 同时 `INSERT ... ON CONFLICT DO UPDATE` token + `UPDATE auth.user SET last_active_at = NOW()`。 |
| `_pre_video_key` | photo_router 内部临时字段（带下划线前缀），不入库，只作为投递 worker 任务时的参数。 |
