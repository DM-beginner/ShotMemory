# 存储模块（Storage）

## 1. 概述

`backend/core/storage/` 通过策略模式抽象出"上传 / 下载 / 删除"接口，由开发环境的本地文件存储实现 + 生产环境的阿里云 OSS 实现（占位）共同构成。所有业务模块（auth 头像、photo_story 照片）都通过统一的 `StorageDep` 依赖注入访问，不直接接触底层 IO。

---

## 2. 抽象基类（`core/storage/interface.py`）

```python
class UploadResult(BaseModel):
    object_key: str   # 相对路径，写入数据库的唯一标识

class StorageStrategy(ABC):
    async def upload_file(self, file: UploadFile) -> UploadResult: ...
    async def upload_bytes(
        self, data: bytes, suffix: str, subdir: str = "thumbnails", stem: str | None = None
    ) -> UploadResult: ...
    async def download_to_file(self, object_key: str) -> Path: ...
    async def delete_file(self, object_key: str) -> bool: ...
```

| 方法 | 用途 | 调用方 |
|------|------|--------|
| `upload_file` | UploadFile（来自 HTTP `multipart/form-data`）→ `originals/` 子目录 | `photo_router.upload_photos`（图片）|
| `upload_bytes` | 程序生成的字节流（缩略图、转码后视频、Live Photo MOV）→ `subdir` 子目录 | `auth_router.upload_avatar`（缩略图）、`photo_router`（MOV）、`worker.parse_photo_exif`（缩略图 + MP4）|
| `download_to_file` | 把 `object_key` 解析为本地可读 `Path`。dev 直接返回原路径；prod 流式下载到临时文件 | `worker._resolve_file_path` |
| `delete_file` | 单文件删除；返回布尔 | `auth_router`（旧头像）、`photo_router`（孤儿回滚）、`worker.delete_oss_files`（异步清理） |

接口签名是**跨模块契约**——切换底层实现时不要改签名，否则所有调用方要跟着改。

---

## 3. `object_key` 命名约定

`object_key` 是数据库唯一持久化的形式，固定为 POSIX 风格相对路径：

```
{UPLOAD_DIR}/originals/{uuid}.{ext}              # 原图
{UPLOAD_DIR}/thumbnails/{stem}.webp              # 缩略图（worker 生成）
{UPLOAD_DIR}/videos/{stem}.mp4                   # 视频（iOS Live Photo MOV → MP4，或 Android 嵌入视频转码）
```

派生关系（`derive_thumbnail_key` / `derive_video_key`，定义在 `services/photo_story/schemas/photo_schema`）：

```
uploads/originals/abc.heic
  ├─ derive_thumbnail_key → uploads/thumbnails/abc.webp
  └─ derive_video_key     → uploads/videos/abc.mp4
```

数据库**只存原图 `object_key`**，缩略图与视频路径都通过派生函数计算，避免冗余字段。

---

## 4. 单例工厂

`get_storage_service()`（`core/storage/__init__.py`）使用 `lru_cache(maxsize=1)` 单例，按 `settings.ENV` 切换：dev → `LocalStorageStrategy`，prod → `AliyunOSSStrategy`。`StorageDep = Annotated[StorageStrategy, Depends(get_storage_service)]`，路由签名直接使用 `storage: StorageDep`。

---

## 5. `LocalStorageStrategy`（开发）

`core/storage/local.py`。构造时确保 `originals/`、`thumbnails/` 子目录存在。

| 行为 | 实现要点 |
|------|---------|
| `upload_file` | `UploadFile.read()` 全量字节；`uuid4().hex + suffix` 命名；`aiofiles` 异步写入 `originals/` |
| `upload_bytes` | 按 `subdir` + 可选 `stem` 写入；缺省 `stem` 时也用 `uuid4().hex` |
| `download_to_file` | 直接返回 `Path(object_key)`，零拷贝 |
| `delete_file` | `Path.unlink()`；不存在时 warning + 返回 false（不报错） |

**静态访问**：仅在 `ENV=dev` 下，`main.py` 挂载 `StaticFiles(directory=".")` 到 `/static`，使前端可直接通过 `http://localhost:5683/static/uploads/originals/...` 取本地文件。生产环境不挂 `/static`，改由 OSS / CDN 提供。

---

## 6. `AliyunOSSStrategy`（生产，**占位实现**）

`core/storage/aliyun.py`。当前所有方法都 `raise NotImplementedError`，构造接受配置 `(access_key_id, access_key_secret, bucket_name, endpoint, cdn_domain)`，源码内已注释好实现思路（`oss2.Bucket.put_object` / `delete_object` / `get_object_to_file`）。

**实施时不要修改 interface 签名**，确保调用方零改动即可切换。完整"上生产前要做什么"清单见 [`docs/production-readiness.md`](../production-readiness.md)。

---

## 7. 配置项（`core/config.py`）

| 配置 | dev 默认 | 用途 |
|------|---------|------|
| `ENV` | `"dev"` | 切换策略 |
| `UPLOAD_DIR` | `"uploads"` | 本地存储根目录 |
| `STATIC_URL_PREFIX` | `"/static"` | StaticFiles 挂载点 |
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` | `""` | OSS 凭证（生产由环境变量注入） |
| `OSS_BUCKET_NAME` / `OSS_ENDPOINT` / `OSS_CDN_DOMAIN` | `""` | OSS bucket 与访问域 |

前端通过 `VITE_STORAGE_BASE_URL` 拼接最终 URL，详见 `docs/frontend-architecture.md` § 10。

---

## 8. 关键源码索引

代码位置：`backend/core/storage/`。`interface.py` 定义抽象、`local.py` 本地实现、`aliyun.py` OSS 占位、`__init__.py` 工厂 + DI。派生路径函数在 `services/photo_story/schemas/photo_schema`；StaticFiles 挂载在 `main.py`。
