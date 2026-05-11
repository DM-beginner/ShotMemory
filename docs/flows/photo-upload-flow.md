# 照片上传 → 处理 → 删除 全链路

跨越 photo / storage / worker / auth 四个模块的端到端时序。本文只解释**跨进程编排**与**失败语义**，具体实现以代码为准（见 `services/photo_story/routers/photo_router` 与 `core/worker`）。

---

## 状态机总览

`PhotoResponse.status` 是计算字段，由 `exif_data` 字段驱动：

```
                     ┌────────────────┐
                     │  uploading     │  POST /v1/photo/uploads（不入库阶段）
                     └────────┬───────┘
                              │ 上传 + 写入 photo + enqueue
                              ▼
                     ┌────────────────┐
                     │  processing    │  exif_data IS NULL
                     │  (Worker 中)   │
                     └────────┬───────┘
                              │ Worker 完成
                ┌─────────────┼──────────────┐
                ▼             ▼              ▼
     ┌────────────────┐ ┌────────────────┐ ┌──────────────────────────┐
     │   completed    │ │   no_exif      │ │ completed (with _error)  │
     │  exif_data:{…} │ │  exif_data:{}  │ │  exif_data:{"_error":…}  │
     └────────────────┘ └────────────────┘ └──────────────────────────┘
```

**契约**：Worker 必定让 `exif_data` 从 `null` 翻成"非 null"——绝不会让前端 `status` 永远停在 `processing`。

---

## 场景 A：常规上传

```
Frontend          API (photo_router)        Storage           arq DB1
   │                 │                        │                │
   ├─ files[] ──────►│                        │                │
   │                 │ All-or-Nothing 校验     │                │
   │                 │ (类型 / 大小 / 数量)     │                │
   │                 │                        │                │
   │                 │── upload_file × N ────►│                │
   │                 │   (失败则反向清理       │                │
   │                 │    uploaded_keys)      │                │
   │                 │                        │                │
   │                 │── PhotoRepo.create_many ────────────────► PostgreSQL
   │                 │── enqueue parse_photo_exif × N ─────────►│
   │◄─ photos[]      │                        │                │
   │   status="processing"                    │                │
```

关键决策点：

1. **All-or-Nothing 校验**：任一文件不合规即 400 拒绝整批，避免半成功状态。
2. **uploaded_keys 反向清理**：上传中途任何异常（含 enqueue 抛错），按已上传顺序反向 `storage.delete_file`，再抛 `50000`，确保 DB 与存储要么全成功要么全为空。
3. **enqueue 在事务后**：先入库再投递任务，避免任务先跑、记录还没在的竞态。

---

## 场景 B：iOS Live Photo 上传

```
Frontend          API                       Storage             Worker             DB
   │                 │                       │                    │                │
   ├─ files=[HEIC,MOV]►│                     │                    │                │
   │                 │ image_files=[HEIC]    │                    │                │
   │                 │ video_files=[MOV]     │                    │                │
   │                 │                       │                    │                │
   │                 │ extract_content_id(MOV)  → "94B5..."       │                │
   │                 │ extract_content_id(HEIC) → "94B5..." 配对   │                │
   │                 │                       │                    │                │
   │                 │── upload_file(HEIC) ─► originals/abc.heic                   │
   │                 │── upload_bytes(MOV, "videos", stem="abc") ─► videos/abc.mov │
   │                 │── INSERT photo (object_key=originals/abc.heic) ────────────►│
   │                 │── enqueue parse_photo_exif("abc.heic", pre_video_key="videos/abc.mov")
   │◄─ photos[]      │                       │                    │                │
   │                 │                       │                    ├─ download HEIC │
   │                 │                       │                    ├─ exif + thumb  │
   │                 │                       │                    │  upload thumbnails/abc.webp
   │                 │                       │                    ├─ download MOV  │
   │                 │                       │                    ├─ ffmpeg → MP4  │
   │                 │                       │                    │  upload videos/abc.mp4
   │                 │                       │                    ├─ delete videos/abc.mov
   │                 │                       │                    ├─ UPDATE photo: │
   │                 │                       │                    │   exif_data,   │
   │                 │                       │                    │   has_video=true
   │                 │                       │                    │   ──────────►  │
   │                 │                       │                    │                │
   │── GET /photo/:id───►│                                         │                │
   │◄─ status=completed, thumbnail_key=…/abc.webp, video_key=…/abc.mp4
```

配对键：Apple `ContentIdentifier`（QuickTime 元数据中的 UUID）。原始 MOV 在 worker 转码后被删除，最终持久化的是 MP4。

---

## 场景 C：Android Motion Photo

无 `video/quicktime` 文件，依赖 EXIF 中的 `MotionPhoto=1` / `MicroVideo=1` 触发。Worker 用 mmap 快路径搜偏移（`MicroVideoOffset` / `MotionPhotoOffset` / `ftypisom/mp42/MSNV/3gp5` box），命中则切片返回视频字节（通常 2-5 MB），未命中走 exiftool 兜底。其余流程与场景 A 末段相同：转码 → 上传 → `has_video=true`。

---

## 场景 D：删除链路

```
DELETE /v1/photo/{id}        或  POST /v1/photo/batch-delete
   │                                {"photo_ids": [...]}（≤ 50）
   │                                  │
   ├─► PhotoRepo.get_keys_for_deletion(db, [ids], user_id)
   │     SELECT object_key, has_video WHERE id IN (...) AND user_id = ?
   │     ↓
   │     [(object_key, has_video)] 或 []
   │
   ├─► 若空 → BaseError(40004)        ← 同一错误防 UUID 枚举攻击
   │
   ├─► PhotoRepo.delete_many(db, [ids], user_id)   # 物理删除
   │
   ├─► oss_keys = [原图, 缩略图, 视频?]
   │
   └─► arq_redis.enqueue_job("delete_oss_files", oss_keys)

   返回：{ "code": 20000, "message": "照片删除成功" }
```

`delete_oss_files`（Worker）：并发删除，失败计数 > 0 抛错触发 arq `max_tries=3` 重试整批。**DB 删是同步短事务，OSS 清理走异步**——前端不会感知 OSS 失败。

---

## 失败语义

### 上传中崩溃

任何 `upload_file` / `upload_bytes` / `create_many` / `enqueue_job` 抛错 → catch all → `for key in uploaded_keys: storage.delete_file(key)`（suppress 全部异常）→ 抛 `BaseError(50000, "批量上传或入库失败，已自动回滚")`。**DB 与存储要么全成功要么全为空，永无半成功状态。**

### Worker 处理崩溃

| 阶段 | 行为 |
|------|------|
| 拉文件失败 | `exif_data = {"_error": "read_file_failed: ..."}`，UPDATE 后正常退出 |
| EXIF 提取异常 | `exif_data = {"_error": "worker_processing_failed"}` |
| 缩略图异常 | 不阻塞主流程，仅 warning，缩略图不生成（前端 `thumbnail_key` 为 null） |
| 视频转码异常 | 不阻塞，`has_video=False`，无视频 |
| 最终 UPDATE 失败 | `db.rollback()` + 抛错 → arq `max_tries=3` 重试 |

**约定**：`exif_data` 字段绝不停留在 NULL 之外的"处理中"状态。前端的 `status` 计算字段就是基于这条契约设计的。

---

## 跨模块依赖关系

```
upload_photos (photo_router)
  ├─ depends on auth.CurrentUser
  ├─ uses storage.upload_file / upload_bytes
  ├─ uses ImageUtil.extract_content_identifier (for iOS pairing)
  ├─ writes via PhotoRepo.create_many
  └─ enqueues parse_photo_exif → arq queue (Redis DB1)

parse_photo_exif (worker)
  ├─ uses storage.download_to_file / upload_bytes / delete_file
  ├─ uses ImageUtil.* (exif / thumbnail / video extract / transcode)
  └─ writes via PhotoRepo.update_after_processing

delete_photo / batch_delete_photos (photo_router)
  ├─ depends on auth.CurrentUser
  ├─ reads & deletes via PhotoRepo
  └─ enqueues delete_oss_files → arq queue (Redis DB1)

delete_oss_files (worker)
  └─ uses storage.delete_file（并发 + 失败重试）

frontend
  ├─ baseApi (Cookie 认证 + 401 自动刷新)
  ├─ photoApi (上传 / 列表 / 详情 / 删除)
  └─ getPhotoUrl / getOriginalUrl / getVideoUrl 拼接 URL（VITE_STORAGE_BASE_URL）
```

---

## 关键配置项

| 配置 | 默认值 | 影响范围 |
|------|--------|---------|
| `MAX_FILES_PER_BATCH` | 50 | photo_router：单次上传上限 |
| `MAX_FILE_SIZE` | 50 MB | photo_router + auth_router 头像 |
| `WORKER_MAX_HEAVY_TASKS` | 3 | worker：Pillow + ffmpeg 并发上限 |
| `WorkerSettings.max_jobs` | 10 | worker：单进程并发任务数 |
| `WorkerSettings.job_timeout` | 120 s | worker：单任务硬超时 |
| `WorkerSettings.max_tries` | 3 | worker：失败重试次数 |
| `Image.MAX_IMAGE_PIXELS` | 50_000_000 | image_util：防解压炸弹 |
| ffprobe / ffmpeg 转码超时 | 10 s / 120 s | image_util |

---

## 关联文档

- 模块视角：[`docs/modules/photo.md`](../modules/photo.md)、[`docs/modules/worker.md`](../modules/worker.md)、[`docs/modules/storage.md`](../modules/storage.md)
- 鉴权细节：[`docs/modules/auth.md`](../modules/auth.md)
- 全局架构：[`docs/architecture.md`](../architecture.md)
