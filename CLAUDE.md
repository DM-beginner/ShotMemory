# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShotMemory is a full-stack photo management app. Backend is Python/FastAPI, frontend is React/TypeScript. Photos are uploaded, EXIF metadata is extracted asynchronously, and GPS coordinates are stored as PostGIS geometry. Stories group photos with a cover image. Motion Photo / Live Photo videos are auto-extracted and transcoded.

## Detailed Documentation

修改任何模块前先阅读对应文档。文档是设计决策、不变量、跨模块契约的唯一信源；具体实现以代码为准。

- 后端总体架构：[`docs/architecture.md`](./docs/architecture.md)
- 前端总体架构：[`docs/frontend-architecture.md`](./docs/frontend-architecture.md)
- 模块文档：
  - [`docs/modules/auth.md`](./docs/modules/auth.md) — 用户认证、双 Token、设备绑定（含 HTTPOnly Cookie + device_id 主线）
  - [`docs/modules/photo.md`](./docs/modules/photo.md) — 照片上传、EXIF、动态照片
  - [`docs/modules/story.md`](./docs/modules/story.md) — 图文故事 CRUD
  - [`docs/modules/storage.md`](./docs/modules/storage.md) — 存储策略
  - [`docs/modules/worker.md`](./docs/modules/worker.md) — arq 后台任务
- 跨模块流程：[`docs/flows/photo-upload-flow.md`](./docs/flows/photo-upload-flow.md)
- 关键设计决策：[`docs/decisions.md`](./docs/decisions.md)
- 术语表：[`docs/glossary.md`](./docs/glossary.md)
- 故障/运维：[`docs/runbook.md`](./docs/runbook.md)
- 上生产前清单：[`docs/production-readiness.md`](./docs/production-readiness.md)
- **文档编写准则**：[`docs/writing-guidelines.md`](./docs/writing-guidelines.md) — 写 / 改任何 `.md` 文档前必读

## AI 工作守则

1. 修任何模块前必读 `docs/modules/<对应>.md`；改架构级行为先看 `docs/architecture.md` + `docs/decisions.md`。
2. 改 schema 必须生成新的 Alembic 迁移（`uv run alembic revision --autogenerate -m "..."`），不要手改已有迁移。
3. **写 / 改任何 `.md` 文档前必读 [`docs/writing-guidelines.md`](./docs/writing-guidelines.md)**——不要在文档里写 `file.py:line` 行号引用、不要复述代码已经清楚表达的内容、不要重复造副本。
4. 写新路由时尽量复用 `SessionDep` / `StorageDep` / `RedisDep` / `CurrentUser` 四个 alias（不强制，但有现成的就别另起）。
5. 前端改动需手工跑一次 `pnpm dev` 用浏览器走一遍黄金路径，不能只靠 `tsc` 通过就声称完成。
6. 不要在 README/docs 里维护代码目录树、字段表、API JSON 样例——这些代码与 `/v1/docs` (OpenAPI) 已是权威来源。

## Development Commands

### Infrastructure
```bash
docker compose up -d              # Start PostgreSQL (PostGIS) + Redis
docker compose down               # Stop containers
docker compose down -v            # Stop + destroy data volumes (resets DB)
```

### Backend (working directory: `backend/`)
```bash
uv sync                                              # Install dependencies (creates .venv)
uv run alembic upgrade head                          # Apply all migrations
uv run alembic revision --autogenerate -m "..."      # Generate migration
uv run alembic downgrade -1                          # Rollback one revision
uv run python -m main                                # Dev server (http://localhost:5683)
uv run arq core.worker.WorkerSettings                # Background task worker (separate terminal)
uv run ruff check . && uv run ruff format .          # Lint + format
uv run pytest                                        # Tests (uses shotmemory_test DB)
uv run locust -f tests/locustfile.py --host=http://localhost:5684
```

### 压测（独立测试 API 实例，不污染开发库）
```bash
# 1. 起测试栈（profile=test，默认 docker compose up 不会启动）
docker compose --profile test up -d --build test_api test_worker  # → 端口 5684

# 2. 首次需初始化测试库（host 直连 docker postgres 跑迁移）
cd backend && DATABASE_URL=postgresql+asyncpg://postgres:SZtu%40143237@localhost:5432/shotmemory_test \
  uv run alembic upgrade head

# 3. 跑 locust（locustfile 有护栏：host 端口=5683 直接 abort）
cd backend && uv run locust -f tests/locustfile.py --host=http://localhost:5684

# 4. 收尾（可选，清理测试 uploads volume）
docker compose --profile test down
docker volume rm shotmemory_test_uploads
```

### Frontend (working directory: `frontend/`)
```bash
pnpm install                      # Install dependencies (rolldown-vite via overrides)
pnpm dev                          # Vite dev server (http://localhost:5173)
pnpm build                        # tsc build then vite build
pnpm check:fix                    # Biome lint + format (fix all)
```

### Pre-commit
```bash
pre-commit run --all-files        # Ruff (backend) + Biome (frontend)
```

## Service Structure（写新模块的 convention）

每个领域 (domain) 在 `backend/services/{domain}/` 下保持以下分层：

```
services/{domain}/
  models/      # SQLAlchemy ORM models（一个领域映射到一个 PostgreSQL schema）
  repos/       # 数据库操作（async session，classmethod 风格）
  routers/     # FastAPI route handlers
  schemas/     # Pydantic request/response models
  utils/       # 业务工具
  exceptions.py
```

当前领域：`auth`、`photo_story`。

## Dependency Injection Aliases

写路由签名时直接使用：

- `SessionDep` — async SQLAlchemy session（`core/database.py`）
- `StorageDep` — storage strategy 实例（`core/storage/__init__.py`）
- `RedisDep` — arq Redis pool（`core/database.py`）
- `CurrentUser` — 从 access_token Cookie 解析的当前用户（`services/auth/routers/user_deps.py`）

## Code Style

**Backend**: Ruff，规则集 `E, F, I, UP, N, B, A, C4, SIM, ASYNC, RUF`，B008 ignored（FastAPI `Depends` in defaults），双引号、LF。Target Python 3.13+，使用现代语法（`X | Y`、小写泛型 `dict[...]` / `list[...]` 等）。

**Frontend**: Biome，双引号、分号、2 空格缩进、88 列。`noUnusedVariables` / `noUnusedImports` 为 error。

## Code Quality Principles

- **Backend**：高并发、高可用、高扩展。充分利用 async/await，代码简洁优雅。
- **Frontend**：组件优先用 HeroUI，Tailwind class 保持简洁（避免冗余 utility）。使用 React 现代语法（hooks、memo、函数组件，避免 class 组件和过时 API）。
