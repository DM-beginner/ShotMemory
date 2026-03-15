# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShotMemory is a full-stack photo management app. Backend is Python/FastAPI, frontend is React/TypeScript. Photos are uploaded, EXIF metadata is extracted asynchronously, and GPS coordinates are stored as PostGIS geometry.

## Development Commands

### Infrastructure
```bash
docker compose up -d              # Start PostgreSQL (PostGIS) + Redis
```

### Backend (working directory: `backend/`)
```bash
uv sync                           # Install dependencies
python -m main                    # Dev server with auto-reload (port 5683)
arq core.worker.WorkerSettings    # Background task worker (separate terminal)
alembic upgrade head              # Apply all migrations
alembic revision --autogenerate -m "description"  # Generate migration
ruff check .                      # Lint
ruff format .                     # Format
```

### Frontend (working directory: `frontend/`)
```bash
pnpm install                      # Install dependencies
pnpm dev                          # Vite dev server (port 5173)
pnpm build                        # Production build (runs tsc then vite build)
pnpm check:fix                    # Biome lint + format (fix all)
```

### Pre-commit
```bash
pre-commit run --all-files        # Run Ruff (backend) + Biome (frontend)
```

## Architecture

### Backend (`backend/`)

FastAPI async app with layered service architecture. Entry point: `main.py` → `create_app()`.

**Service structure** — each domain follows this pattern:
```
services/{domain}/
  models/      # SQLAlchemy ORM models
  repos/       # Database operations (async session)
  routers/     # FastAPI route handlers
  schemas/     # Pydantic request/response models
  utils/       # Business logic helpers
  exceptions.py
```

Current domains: `auth`, `photo_story`.

**Core framework** (`core/`):
- `config.py` — pydantic-settings, reads from `.env` file
- `database.py` — async SQLAlchemy engine + session factory
- `security.py` — JWT + Argon2 password utilities
- `exceptions.py` — `APIStatus` enum + `BaseError` class
- `unify_response.py` — standardized JSON responses (orjson)
- `storage/` — strategy pattern: `LocalStorageStrategy` (dev) / `AliyunOSSStrategy` (prod)
- `worker.py` — arq task definitions (`parse_photo_exif`, `delete_oss_files`)

**Dependency injection aliases** (used in router signatures):
- `SessionDep` — async SQLAlchemy session
- `StorageDep` — storage strategy instance
- `RedisDep` — arq Redis pool
- `CurrentUser` — authenticated user from JWT cookie

**Database**: PostgreSQL 16 with PostGIS. Schemas: `auth`, `photo_story`. Alembic migrations use date-based filenames (`YYYY_MM_DD_HHMM-{rev}_{slug}.py`).

**Background processing**: arq workers consume Redis DB 1. Photo uploads trigger async EXIF parsing, thumbnail generation (WebP, max 400px), and optional video extraction for motion photos.

### Frontend (`frontend/`)

React 19 + TypeScript with Redux Toolkit for state management.

**Key patterns**:
- RTK Query for all API calls — defined in `services/{domain}/redux/api/`. The `baseApi` (`app/baseApi.ts`) handles automatic token refresh on 401.
- Feature-based organization under `services/` mirroring backend domains
- HeroUI component library with Tailwind CSS 4 and next-themes for dark mode
- React Router v7 with `MainLayout` wrapper
- Vite uses `rolldown-vite` (aliased via pnpm overrides)

**API configuration**: `VITE_BACKEND_HOST` and `VITE_BACKEND_PREFIX=/v1` env vars. All endpoints are prefixed with `/v1`.

## Code Style

**Backend**: Ruff with double quotes, LF line endings. Rules: E, F, I, UP, N, B, A, C4, SIM, ASYNC, RUF. B008 is ignored (FastAPI `Depends` in defaults). Target: Python 3.13+.

**Frontend**: Biome with double quotes, semicolons, 2-space indent, 88 char line width. `noUnusedVariables` and `noUnusedImports` are errors. `noConsoleLog` and `noExplicitAny` are warnings.

## Auth Flow

JWT tokens delivered via HTTPOnly cookies (not Authorization headers). Access token (30min) + refresh token (7 days) with device-aware rotation. The frontend's RTK Query `baseQuery` automatically retries with a refreshed token on 401.
