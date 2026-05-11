# Worker 模块（arq）

## 1. 概述

`backend/core/worker.py` 是独立运行的 arq Worker 进程，专责把 CPU/IO 密集的工作（EXIF 解析、Pillow 缩略图、ffmpeg 转码、批量删 OSS）从 HTTP 请求路径中卸载，避免拖垮 FastAPI 主服务的事件循环与连接池。

启动命令（`backend/` 目录下，独立终端）：

```bash
uv run arq core.worker.WorkerSettings
```

主服务通过 `RedisDep` 注入的 arq 队列（Redis DB1）`enqueue_job(func_name, *args)` 投递任务。

---

## 2. WorkerSettings

注册任务：`parse_photo_exif`、`delete_oss_files`。关键约束：

- `max_jobs = 10` — 单 Worker 进程并发任务上限
- `job_timeout = 120s` — 单任务硬超时
- `max_tries = 3` — 失败重试次数（arq 默认 5，此处收紧）
- `health_check_interval = 30s`
- `on_startup` 预热数据库连接池（`SELECT 1`）；`on_shutdown` 调 `engine.dispose()`

完整字段定义见 `core/worker.WorkerSettings`。

---

## 3. Worker 内部数据库会话

Worker 进程独立于 FastAPI 请求生命周期，单独拥有一份 SQLAlchemy 引擎（`pool_size=5, max_overflow=5`），显著小于主服务（50+20）——因为 Worker 在 CPU 密集计算阶段**不持有**数据库连接：先把 EXIF / 缩略图算完，再开短事务一次性 UPDATE。

---

## 4. 并发控制

```python
_heavy_sem = asyncio.Semaphore(settings.WORKER_MAX_HEAVY_TASKS)   # 默认 3
```

被两类重计算包裹：

- Pillow 解压 + 生成缩略图（`generate_thumbnail_from_path`）
- ffmpeg 转码（`prepare_video_*`）

允许 `max_jobs=10` 个任务并行，但任意时刻最多 3 个进入"烧 CPU"阶段，避免 ffmpeg 集体爆掉机器。

---

## 5. 任务：`parse_photo_exif`

签名：`parse_photo_exif(ctx, photo_id: str, object_key: str, pre_video_key: str | None)`

### 5.1 流程（行为描述，不贴代码）

1. **取本地路径**：dev 直接 `Path(object_key)`；prod `storage.download_to_file` 流式下载到临时文件。
2. **进入 `_heavy_sem`**：并行跑 EXIF 提取 + 缩略图生成（`asyncio.gather(..., return_exceptions=True)`）。缩略图成功则上传到 `thumbnails/{stem}.webp`。
3. **GPS 落库**：经纬度都不为 `None` 且不全为 0.0 时，写 `location_wkt = "POINT(<lng> <lat>)"`。
4. **视频处理**（如适用）：
   - `pre_video_key` 存在（iOS Live Photo）：下载 MOV → 转码 MP4 → 上传 `videos/{stem}.mp4` → 删除原 MOV → `has_video=True`。
   - 否则 EXIF 含 `MotionPhoto` / `MicroVideo`（Android）：mmap 快路径提取嵌入视频，失败兜底 exiftool → 转码 MP4 → 上传 → `has_video=True`。
5. **短事务 UPDATE**：`PhotoRepo.update_after_processing(photo_id, PhotoWorkerUpdate{...})` 一次性写回 `width / height / taken_at / exif_data / has_video / location_wkt`。

### 5.2 错误回写契约

`exif_data` 字段是隐式状态机（参见 `docs/modules/photo.md` § 4），约定：

| 阶段 | `exif_data` |
|------|-------------|
| 文件解析失败（如 storage 拉文件失败）| `{"_error": "read_file_failed: ..."}` |
| 元数据 `gather` 异常或返回 None | `{"_error": "worker_processing_failed"}` |
| 解析出空 EXIF（无元数据） | `{}` |
| 成功 | 真实字典（命名空间合并 + 二进制裁剪） |

**Worker 必须把 `exif_data` 从 `null` 翻成"非 null"**，否则前端的 `status` 计算字段会一直停在 `processing`。这是与 photo 模块的双向契约。

### 5.3 缩略图与视频上传约定

- 缩略图：`upload_bytes(suffix=".webp", subdir="thumbnails", stem=Path(object_key).stem)` → 派生路径 `uploads/thumbnails/{stem}.webp`
- 视频：`upload_bytes(suffix=".mp4", subdir="videos", stem=Path(object_key).stem)` → 派生路径 `uploads/videos/{stem}.mp4`

派生函数 `derive_thumbnail_key` / `derive_video_key` 在响应序列化时即时计算，必须能命中这两个路径。

---

## 6. 任务：`delete_oss_files`

签名：`delete_oss_files(ctx, keys: list[str])`。

行为：并发 `storage.delete_file(k) for k in keys`，`asyncio.gather(..., return_exceptions=True)` 统计失败数；> 0 则抛错触发 arq 按 `max_tries=3` 重试整批。触发方（`photo_router.delete_photo` / `batch_delete_photos`）一次性把 `[原图, 缩略图, 视频?]` 全推进来，避免散单。

---

## 7. EXIF 处理细节（`services/photo_story/utils/image_util.py`）

### 7.1 双轨 API

- 基于**路径**（核心）：`extract_metadata_from_path` / `generate_thumbnail_from_path` / `prepare_video_from_path` / `extract_embedded_video_from_path`
- 基于**字节**（兼容旧调用）：同名去掉 `_from_path`，内部写临时文件后调用路径版

Worker 在拿到本地路径后默认走路径 API，零内存中转。

### 7.2 命名空间优先级（高 → 低）

```
EXIF > Composite > MakerNotes > XMP > IPTC > File > ExifTool
```

`_flatten_by_priority`：先把所有非优先命名空间合并，再按倒序覆盖优先命名空间。这意味着 `EXIF` 的字段会最终覆盖任何同名的下位字段（例如 `EXIF:DateTimeOriginal` 优先于 `XMP:DateTimeOriginal`）。

### 7.3 二进制大字段裁剪

`_filter_binary` 移除以下键，避免把几十 KB 的 base64 缩略图重复落库：

```
ThumbnailImage, PreviewImage, JpgFromRaw, OtherImage,
MPImage1, MPImage2, PreviewTIFF, PreviewIPTC
```

### 7.4 GPS 解析

`ImageMetadata._parse_gps` 支持三种格式：

- 纯数字 + 方向后缀：`"110.6164 E"` → 110.6164
- DMS：`"35 deg 40' 20.5\" N"` → 35.6724
- 纯数值（结合 `*Ref`）：`110.6164` + `Ref="W"` → -110.6164

### 7.5 缩略图

- `Image.MAX_IMAGE_PIXELS = 50_000_000`（约 7000×7000，防解压炸弹）
- `ImageOps.exif_transpose` 修正 EXIF Orientation
- LANCZOS 缩放到 ≤400×400，输出 WebP `quality=60, method=6`
- 解压超限抛 `ThumbnailGenerationError`

### 7.6 动态照片视频提取

`_extract_video_from_file` 两层路径：

1. **快路径（mmap）**：内存映射文件，按以下偏移搜索——`MicroVideoOffset` (Google Camera) / `MotionPhotoOffset` (Google/Samsung) / `ftypisom/mp42/MSNV/3gp5` 二进制 box（从文件后半段开始，避 EXIF 误命中）。校验 `len > 1000` 且开头含 `ftyp`。
2. **慢兜底（exiftool）**：`exiftool -b -EmbeddedVideoFile -MicroVideo <path>`，子进程 30s 超时。

### 7.7 视频转码（`_prepare_video_from_file`）

`_needs_transcode` 用 ffprobe 探测 `codec_name`：

- H.264 → 仅 remux：`ffmpeg -i in -c copy -movflags +faststart -y out.mp4`
- 其他（H.265 / HEVC）→ 真转码：`-c:v libx264 -preset fast -crf 23 -c:a aac -movflags +faststart`
- 子进程 120s 硬超时，输出文件总在 `finally` 中清理

### 7.8 Apple Live Photo ContentIdentifier

`_extract_content_identifier_sync` 在 HEIC / MOV 文件中搜索如下键，任一命中即返回：

```
Apple:ContentIdentifier
Keys:ContentIdentifier
QuickTime:ContentIdentifier
*ContentIdentifier   ← fallback 后缀匹配
```

主服务 `photo_router.upload_photos` 用此函数把同批 HEIC 与 MOV 配对成 `(image_idx → video_bytes)` 字典。

---

## 8. 失败处理与可观测性

- 所有外部 IO（exiftool、ffmpeg、storage）都用 `logger.exception` 记录，错误信息写入 stderr / stdout
- ffmpeg 输出的 stderr 仅截取最后 1000 字节，避免日志爆量
- `_heavy_sem` 失败不会泄露许可（`async with` 自动释放）
- 短事务 `PhotoRepo.update_after_processing` 失败 → 显式 `db.rollback()` 后 `raise`，触发 arq 重试

---

## 9. 关键源码索引

- Worker 入口 + 任务注册：`backend/core/worker.py`
- 图像 / 视频处理：`backend/services/photo_story/utils/image_util.py`
- EXIF schema：`services/photo_story/schemas/exif_schema.py` + `photo_schema.PickedExif`
- Worker 回写 schema 与 Repo：`schemas/photo_schema.PhotoWorkerUpdate`、`repos/photo_repo.update_after_processing`
