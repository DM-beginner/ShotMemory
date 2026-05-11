# 照片模块

## 1. 概述

`backend/services/photo_story/` 中的 photo 子模块负责：

- 批量上传图片（含 iOS Live Photo 配对、Android Motion Photo）
- 异步 EXIF 解析、缩略图生成（WebP 400px）、嵌入视频提取与转码
- GPS 经纬度持久化为 PostGIS Geometry，供 3D 地球可视化使用
- 照片 CRUD（含批量删除）+ OSS 文件异步清理

完整跨模块上传链路见 [`docs/flows/photo-upload-flow.md`](../flows/photo-upload-flow.md)。

---

## 2. 数据模型 — `photo_story.photo`

字段定义以 `services/photo_story/models/photo_model.py` 为准。下表只列**非显然**字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| object_key | VARCHAR(500) | 原图 OSS 相对路径，如 `uploads/originals/abc.heic` |
| has_video | BOOL | 是否存在配对/嵌入视频（iOS Live Photo 或 Android Motion Photo） |
| location_wkt | Geometry(POINT, 4326) NULL | GPS 坐标，WGS84；ORM 层是 `geoalchemy2.WKBElement`，响应序列化转 GeoJSON Point |
| exif_data | JSONB(none_as_null=True) NULL | 完整 EXIF；隐式状态机（详见第 4 节） |
| taken_at | TIMESTAMPTZ NULL DEFAULT now() | EXIF DateTimeOriginal/DateTimeDigitized/CreateDate 优先级；缺失时保留上传时间 |

索引：`(user_id)`、`(object_key)`、`(taken_at)`。

---

## 3. 路径派生约定

数据库**只存原图 `object_key`**，缩略图与视频路径通过 `derive_thumbnail_key` / `derive_video_key`（`services/photo_story/schemas/photo_schema.py`）即时计算：

| 衍生类型 | 规则 |
|----------|------|
| 缩略图 | `uploads/originals/abc.heic` → `uploads/thumbnails/abc.webp` |
| 视频   | `uploads/originals/abc.heic` → `uploads/videos/abc.mp4` |

衍生路径仅在条件成立时返回：

- `thumbnail_key` 仅在 `exif_data is not None`（即处理已结束）时返回
- `video_key` 仅在 `has_video == true` 时返回

---

## 4. 处理状态机

`PhotoResponse.status` 是计算字段，绝不落库：

| `exif_data` | `status` | 含义 |
|-------------|----------|------|
| `null` | `processing` | Worker 还没回写，前端可继续轮询 |
| `{}`   | `no_exif`    | Worker 完成，但照片本身不含 EXIF |
| `{ ... 真实数据 ... }` | `completed` | 处理完成，可能含 `_error` 键表示局部失败 |

> 失败也会回写 `exif_data = {"_error": "<reason>"}`，前端按 `completed` 处理但可读 `_error` 字段做降级显示。**约定：`exif_data` 永远不会停留在 `null` 之外的"处理中"状态**——这是 Worker 的回写契约（详见 `docs/modules/worker.md` § 5.2）。

---

## 5. API 接口

所有接口前缀 `/v1/photo`，需 `CurrentUser`。完整请求/响应字段见 `/v1/docs`，以下只列**非显然**语义。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/photo/uploads` | POST | 批量上传，`multipart/form-data` 字段 `files`。校验阈值：单次 ≤ `MAX_FILES_PER_BATCH=50`、单文件 ≤ `MAX_FILE_SIZE=50 MB`、ContentType 白名单含 `video/quicktime`（仅作 Live Photo 视频部分）。**All-or-Nothing 校验**：任一不合规直接 400 拒绝整批 |
| `/photo` | GET | 列表，`?limit=&offset=`，按 `taken_at DESC`。`total` 字段当前是**当前页数量**（避免 COUNT(*) 慢查询），前端通过返回数量是否等于 limit 判断是否还有下一页 |
| `/photo/{id}` | GET | 详情，归属当前用户 |
| `/photo/{id}` | PATCH | 当前仅支持覆盖 `exif_data` |
| `/photo/{id}` | DELETE | 单删；`PhotoRepo.get_keys_for_deletion` 一次性提取 `(object_key, has_video)` **同时完成越权拦截**（查不到一律 `40004`，防 UUID 枚举攻击）；DB 同步删，OSS 走 `arq` 异步清理 |
| `/photo/batch-delete` | POST | 批删，请求体 `photo_ids[]` ≤ 50；逻辑同上 |

错误码段位见 `docs/architecture.md` § 11。

---

## 6. 业务规则

1. **All-or-Nothing 校验**：任意一张文件类型/大小不合规即 400 拒绝整批，避免半成功状态。
2. **iOS Live Photo 自动配对**：HEIC（或 JPG）+ MOV 通过 Apple `ContentIdentifier`（QuickTime 元数据）配对。配对成功后视频与图片同 stem 入 `videos/`，并把 `pre_video_key` 一起塞进 worker 任务。
3. **失败回滚**：上传中途失败时按 `uploaded_keys` 反向清理已落盘的文件，避免孤儿；只回滚已上传的，不再触发 worker。
4. **越权拦截集中在 Repo 层**：`get_keys_for_deletion` 用 `WHERE id IN (...) AND user_id = ?` 一次性过滤，路由层只判断"返回是否为空"。
5. **OSS 清理走异步**：DB 删除是同步短事务，OSS 清理交给 arq（带 `max_tries=3` 重试）。前端不会感知 OSS 清理失败。
6. **GPS 清理**：worker 端只有当 `latitude`、`longitude` 都不为 `None` 且不全为 0.0 时才回写 `POINT(lng lat)`（避免 (0,0) 几内亚湾的"默认坐标"污染）。
7. **`taken_at` 兜底**：表上 `server_default=func.now()`；EXIF 缺失时保留上传时间。
8. **`thumbnail_key` 仅在处理结束后返回**：未处理完时为 null，前端不会请求一个 404 缩略图。
9. **不返回完整 URL**：响应只给 `object_key/thumbnail_key/video_key`，前端用 `${VITE_STORAGE_BASE_URL}/...` 拼接（详见 `docs/frontend-architecture.md` § 10）。
10. **删除不 invalidate Photo tag**：前端 `photoApi` 显式不打 `invalidatesTags`，由调用方（PhotoWall）通过 `onDeleted` 直接修改本地状态，避免 RTK refetch 与 Masonry 虚拟列表冲突。

---

## 7. 响应字段对照（`PhotoResponse`）

| 字段 | 来源 | 备注 |
|------|------|------|
| `id` / `user_id` / `object_key` | DB 字段 | |
| `has_video` | DB 字段 | `exclude=True` 不出现在响应里，仅供 `video_key` 计算 |
| `thumbnail_key` | computed | 仅在处理完成时返回 |
| `video_key` | computed | 仅在 `has_video=true` 时返回 |
| `width` / `height` | DB 字段 | |
| `location_wkt` | computed | 由 `WKBElement` 转 `{type:"Point", coordinates:[lng, lat]}` |
| `exif_data` | DB 字段 | 可能含 `_error` 键 |
| `taken_at` / `created_at` | DB 字段 | 带时区 |
| `status` | computed | `processing` / `no_exif` / `completed` |

---

## 8. 依赖关系

| 依赖于 | 用途 |
|--------|------|
| `services.auth` | `CurrentUser` 注入 |
| `core.storage` | 上传 / 删除原图、视频 |
| `core.worker` | enqueue `parse_photo_exif`、`delete_oss_files` |
| `services.photo_story.utils.image_util` | EXIF / 缩略图 / 视频处理（worker 用） |

| 被依赖 | 用途 |
|--------|------|
| Story 模块 | 校验照片归属、推导封面缩略图 |
| 前端 | 瀑布流、详情页、3D 地球 |

---

## 9. 关键源码索引

代码位置：`backend/services/photo_story/`。
- 路由 + Repo + Schema + Model：`routers/photo_router`、`repos/photo_repo`、`schemas/photo_schema`、`models/photo_model`
- 派生路径函数 `derive_thumbnail_key` / `derive_video_key` + 状态计算 `PhotoResponse.status`：`schemas/photo_schema`
- 图像 / 视频处理（Pillow + ffmpeg + exiftool）：`utils/image_util`
- Worker 回写 schema `PhotoWorkerUpdate` 与回写 repo `update_after_processing`：分别在 `schemas/photo_schema` 与 `repos/photo_repo`
- Worker 任务定义：`backend/core/worker.py`
