# ShotMemory

一款全栈照片管理应用，让每一张照片都成为值得珍藏的记忆。上传照片后自动解析 EXIF 元数据，提取 GPS 坐标在 3D 地球上可视化，支持动态照片（Motion Photo / Live Photo）播放，并可将照片组织为图文故事。

## 功能特性

- **照片管理** — 上传、瀑布流浏览、EXIF 信息面板、缩略图自动生成（WebP）
- **地理可视化** — GPS 坐标自动提取，MapLibre GL 3D 地球展示，Supercluster 聚合标记
- **动态照片** — 自动识别 Android MotionPhoto / iOS Live Photo，提取嵌入视频并转码为 H.264 MP4
- **图文故事** — 创建故事并关联最多 9 张照片，支持封面、排序、编辑
- **用户认证** — JWT 双 Token（HTTPOnly Cookie），设备感知轮转，自动静默刷新
- **头像上传** — 自动裁剪缩放为 200px WebP 缩略图
- **深色模式** — 基于 next-themes 的主题切换

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn + uvloop |
| **数据库** | PostgreSQL 16 + PostGIS 3.4（空间地理查询） |
| **ORM** | SQLAlchemy 2.0（全异步 asyncpg 驱动） |
| **任务队列** | arq + Redis 7（物理隔离：缓存 DB0 / 队列 DB1） |
| **图像处理** | Pillow（缩略图）+ pyexiftool（EXIF 解析）+ ffmpeg（视频转码） |
| **认证** | PyJWT + Argon2（pwdlib） |
| **存储** | 策略模式：LocalStorage（开发）/ Aliyun OSS（生产） |
| **前端框架** | React 19 + TypeScript 5.9 |
| **状态管理** | Redux Toolkit + RTK Query |
| **UI 组件** | HeroUI + Tailwind CSS 4 + Framer Motion |
| **地图** | MapLibre GL + react-map-gl + Supercluster |
| **瀑布流** | Masonic（虚拟化瀑布流） |
| **构建工具** | rolldown-vite（Rust 加速） |
| **代码质量** | Ruff（后端）+ Biome（前端）+ pre-commit |

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React 19)                   │
│  PhotoWall ─ PhotoDetail ─ PhotoGlobe ─ StoryEditor     │
│         RTK Query ──► baseQueryWithReauth                │
│              (401 → 自动刷新 → 重试)                      │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPOnly Cookie (JWT)
┌──────────────────────▼──────────────────────────────────┐
│                Backend (FastAPI async)                    │
│                                                          │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  auth   │  │  photo_story │  │   core 框架       │    │
│  │ Router  │  │   Router     │  │  ┌────────────┐   │    │
│  │ Repo    │  │   Repo       │  │  │ Storage    │   │    │
│  │ Schema  │  │   Schema     │  │  │ (Strategy) │   │    │
│  │ Model   │  │   Model      │  │  └────────────┘   │    │
│  └─────────┘  └──────┬───────┘  │  Security / DB    │    │
│                      │          │  UnifyResponse     │    │
│                      │          └──────────────────┘    │
└──────────────────────┼──────────────────────────────────┘
                       │ arq enqueue
┌──────────────────────▼──────────────────────────────────┐
│              arq Worker (独立进程)                        │
│  parse_photo_exif: EXIF 提取 + 缩略图生成 + 视频转码     │
│  delete_oss_files: 批量文件清理（重试机制）                │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌───────────┐
   │ PostgreSQL│  │  Redis   │  │ Storage   │
   │ + PostGIS │  │ DB0 缓存  │  │ Local/OSS │
   │           │  │ DB1 队列  │  │           │
   └──────────┘  └──────────┘  └───────────┘
```

## 技术亮点

### 后端

- **全链路异步** — 从 HTTP 请求到数据库查询（asyncpg）到文件 I/O（aiofiles）全部 async/await，CPU 密集任务（EXIF 解析、Pillow 缩略图）通过 `asyncio.to_thread` 卸载到线程池
- **PostGIS 空间查询** — GPS 坐标存储为 `Geometry(POINT, SRID=4326)`，支持 WGS84 标准空间索引和地理距离查询
- **动态照片双轨提取** — 纯 Python 内存快路径（正则匹配 ftyp box 零磁盘 I/O）+ exiftool 子进程慢兜底，覆盖 Google/Samsung/OPPO/Apple 全厂商格式
- **视频智能转码** — ffprobe 自动探测编码，H.264 仅 remux（毫秒级），H.265/HEVC 才真正转码，输出 faststart MP4
- **存储策略模式** — `StorageStrategy` 抽象基类，开发环境 LocalStorage 零配置启动，生产环境无缝切换 Aliyun OSS
- **EXIF 命名空间优先级展平** — 自定义 7 级命名空间优先级（EXIF > Composite > MakerNotes > XMP > IPTC > File > ExifTool），解决多命名空间冲突
- **arq 物理隔离** — 缓存（DB0）和任务队列（DB1）分库，高并发场景下互不干扰
- **设备感知 Token 轮转** — Refresh Token 以 device_id 为锚点 UPSERT，支持多设备并行登录，单设备 Token 自动覆盖

### 前端

- **RTK Query 自动重认证** — `baseQueryWithReauth` 拦截 401 响应，静默调用 `/auth/refresh` 后无感重试原请求
- **3D 地球可视化** — MapLibre GL globe 投影 + Supercluster 点聚合，低缩放级别球体视图，高缩放级别自动切换 Mercator
- **虚拟化瀑布流** — Masonic 库实现窗口化渲染，IntersectionObserver 哨兵元素触发无限滚动加载
- **照片详情页** — 支持左右滑动切换、EXIF 面板展示、缩略图条快速跳转、动态照片视频播放
- **rolldown-vite 构建** — 基于 Rust 的 Rolldown 打包器替代 Rollup，显著提升构建速度

## 快速开始

### 环境要求

- Python 3.13+、Node.js 20+、pnpm、Docker
- 系统依赖：exiftool、ffmpeg

### 启动基础设施

```bash
docker compose up -d    # PostgreSQL (PostGIS) + Redis
```

### 启动后端

```bash
cd backend
uv sync                         # 安装依赖
alembic upgrade head             # 数据库迁移
python -m main                   # API 服务 (端口 5683)
arq core.worker.WorkerSettings   # 后台任务 Worker (新终端)
```

### 启动前端

```bash
cd frontend
pnpm install     # 安装依赖
pnpm dev         # 开发服务器 (端口 5173)
```

## 项目结构

```
ShotMemory/
├── backend/
│   ├── main.py                      # 应用入口，FastAPI app factory
│   ├── core/
│   │   ├── config.py                # pydantic-settings 配置
│   │   ├── database.py              # 异步 SQLAlchemy 引擎 + 会话
│   │   ├── security.py              # JWT + Argon2 密码工具
│   │   ├── worker.py                # arq 后台任务定义
│   │   ├── storage/                 # 存储策略 (Local / Aliyun OSS)
│   │   ├── unify_response.py        # 统一 JSON 响应 (orjson)
│   │   └── exceptions.py            # APIStatus 枚举 + BaseError
│   ├── services/
│   │   ├── auth/                    # 认证域：注册/登录/刷新/登出/注销
│   │   └── photo_story/             # 照片故事域：照片上传/故事 CRUD
│   └── alembic/                     # 数据库迁移
├── frontend/
│   ├── src/
│   │   ├── app/                     # Redux store + RTK Query baseApi
│   │   ├── layouts/                 # MainLayout + Header
│   │   ├── services/
│   │   │   ├── auth/                # 认证：登录弹窗 + authSlice
│   │   │   ├── photo/               # 照片：瀑布流/详情/地球/上传
│   │   │   └── story/               # 故事：列表/编辑器/详情
│   │   └── styles/                  # Tailwind CSS + HeroUI 主题
│   └── package.json
└── docker-compose.yml               # PostgreSQL + Redis
```
