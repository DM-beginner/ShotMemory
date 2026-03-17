# ShotMemory

A full-stack photo management app that turns every shot into a memory worth keeping. Photos are automatically parsed for EXIF metadata upon upload, GPS coordinates are visualized on a 3D globe, Motion Photos and Live Photos are detected and played back, and photos can be organized into illustrated stories.

## Features

- **Photo Management** — Upload, masonry-grid browsing, EXIF info panel, auto-generated WebP thumbnails
- **Geo Visualization** — Automatic GPS extraction, MapLibre GL 3D globe display, Supercluster marker aggregation
- **Motion Photos** — Auto-detection of Android MotionPhoto / iOS Live Photo with embedded video extraction and H.264 MP4 transcoding
- **Photo Stories** — Create stories with up to 9 associated photos, cover image, drag-to-reorder, and editing
- **Authentication** — Dual JWT tokens via HTTPOnly cookies, device-aware rotation, silent auto-refresh
- **Avatar Upload** — Automatic crop and resize to 200px WebP thumbnails
- **Dark Mode** — Theme switching powered by next-themes

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend Framework** | FastAPI + Uvicorn + uvloop |
| **Database** | PostgreSQL 16 + PostGIS 3.4 (geospatial queries) |
| **ORM** | SQLAlchemy 2.0 (fully async via asyncpg) |
| **Task Queue** | arq + Redis 7 (physically isolated: cache DB0 / queue DB1) |
| **Image Processing** | Pillow (thumbnails) + pyexiftool (EXIF parsing) + ffmpeg (video transcoding) |
| **Auth** | PyJWT + Argon2 (pwdlib) |
| **Storage** | Strategy pattern: LocalStorage (dev) / Aliyun OSS (prod) |
| **Frontend Framework** | React 19 + TypeScript 5.9 |
| **State Management** | Redux Toolkit + RTK Query |
| **UI Components** | HeroUI + Tailwind CSS 4 + Framer Motion |
| **Map** | MapLibre GL + react-map-gl + Supercluster |
| **Masonry Grid** | Masonic (virtualized masonry layout) |
| **Build Tool** | rolldown-vite (Rust-powered) |
| **Code Quality** | Ruff (backend) + Biome (frontend) + pre-commit |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React 19)                   │
│  PhotoWall ─ PhotoDetail ─ PhotoGlobe ─ StoryEditor     │
│         RTK Query ──► baseQueryWithReauth                │
│            (401 → auto refresh → retry)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPOnly Cookie (JWT)
┌──────────────────────▼──────────────────────────────────┐
│                Backend (FastAPI async)                    │
│                                                          │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  auth   │  │  photo_story │  │   Core Framework  │    │
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
│              arq Worker (separate process)               │
│  parse_photo_exif: EXIF + thumbnail + video transcode    │
│  delete_oss_files: batch file cleanup (with retry)       │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌───────────┐
   │ PostgreSQL│  │  Redis   │  │ Storage   │
   │ + PostGIS │  │ DB0 cache│  │ Local/OSS │
   │           │  │ DB1 queue│  │           │
   └──────────┘  └──────────┘  └───────────┘
```

## Technical Highlights

### Backend

- **End-to-end async** — From HTTP handling to database queries (asyncpg) to file I/O (aiofiles), everything is async/await. CPU-bound tasks (EXIF parsing, Pillow thumbnails) are offloaded to thread pools via `asyncio.to_thread`
- **PostGIS geospatial queries** — GPS coordinates stored as `Geometry(POINT, SRID=4326)` with WGS84 spatial indexing for geographic distance queries
- **Dual-track Motion Photo extraction** — Pure-Python in-memory fast path (regex-matching ftyp boxes, zero disk I/O) + exiftool subprocess fallback, covering Google/Samsung/OPPO/Apple formats
- **Smart video transcoding** — ffprobe auto-detects codec; H.264 streams are only remuxed (milliseconds), while H.265/HEVC is actually transcoded; output is faststart MP4
- **Storage strategy pattern** — `StorageStrategy` abstract base class; LocalStorage for zero-config dev, seamlessly swappable to Aliyun OSS in production
- **EXIF namespace priority flattening** — Custom 7-level namespace priority (EXIF > Composite > MakerNotes > XMP > IPTC > File > ExifTool), resolving cross-namespace key conflicts
- **arq physical isolation** — Cache (DB0) and task queue (DB1) on separate Redis databases, preventing mutual interference under high concurrency
- **Device-aware token rotation** — Refresh tokens use device_id as an UPSERT anchor, supporting concurrent multi-device login with automatic per-device token replacement

### Frontend

- **RTK Query auto-reauthentication** — `baseQueryWithReauth` intercepts 401 responses, silently calls `/auth/refresh`, and seamlessly retries the original request
- **3D globe visualization** — MapLibre GL globe projection + Supercluster point aggregation; globe view at low zoom, automatic Mercator switch at high zoom
- **Virtualized masonry grid** — Masonic library for windowed rendering with IntersectionObserver sentinel elements triggering infinite scroll
- **Photo detail page** — Swipe navigation, EXIF panel, thumbnail strip for quick jumping, Motion Photo video playback
- **rolldown-vite build** — Rust-based Rolldown bundler replacing Rollup for significantly faster builds

## Getting Started

### Prerequisites

- Python 3.13+, Node.js 20+, pnpm, Docker
- System dependencies: exiftool, ffmpeg

### Start Infrastructure

```bash
docker compose up -d    # PostgreSQL (PostGIS) + Redis
```

### Start Backend

```bash
cd backend
uv sync                         # Install dependencies
alembic upgrade head             # Run database migrations
python -m main                   # API server (port 5683)
arq core.worker.WorkerSettings   # Background worker (new terminal)
```

### Start Frontend

```bash
cd frontend
pnpm install     # Install dependencies
pnpm dev         # Dev server (port 5173)
```

## Project Structure

```
ShotMemory/
├── backend/
│   ├── main.py                      # Entry point, FastAPI app factory
│   ├── core/
│   │   ├── config.py                # pydantic-settings configuration
│   │   ├── database.py              # Async SQLAlchemy engine + session
│   │   ├── security.py              # JWT + Argon2 password utilities
│   │   ├── worker.py                # arq background task definitions
│   │   ├── storage/                 # Storage strategies (Local / Aliyun OSS)
│   │   ├── unify_response.py        # Unified JSON responses (orjson)
│   │   └── exceptions.py            # APIStatus enum + BaseError
│   ├── services/
│   │   ├── auth/                    # Auth domain: register/login/refresh/logout
│   │   └── photo_story/             # Photo-story domain: upload/CRUD
│   └── alembic/                     # Database migrations
├── frontend/
│   ├── src/
│   │   ├── app/                     # Redux store + RTK Query baseApi
│   │   ├── layouts/                 # MainLayout + Header
│   │   ├── services/
│   │   │   ├── auth/                # Auth: login modal + authSlice
│   │   │   ├── photo/               # Photo: masonry/detail/globe/upload
│   │   │   └── story/               # Story: list/editor/detail
│   │   └── styles/                  # Tailwind CSS + HeroUI theme
│   └── package.json
└── docker-compose.yml               # PostgreSQL + Redis
```
