# ShotMemory

一款全栈照片管理应用，让每一张照片都成为值得珍藏的记忆。上传照片后自动解析 EXIF 元数据，提取 GPS 坐标在 3D 地球上可视化，支持动态照片（Motion Photo / Live Photo）播放，并可将照片组织为图文故事。

技术栈：FastAPI（asyncpg + PostgreSQL/PostGIS + arq + Redis）后端 + React 19 / Vite 前端。完整架构、设计决策、模块行为见 [`docs/`](./docs/)。日常开发命令与 AI 协作守则见 [`CLAUDE.md`](./CLAUDE.md)。

---

## 环境要求

| 类别 | 工具 | 推荐版本 | 用途 |
|------|------|----------|------|
| 运行时 | Python | 3.13+ | 后端 |
| 运行时 | Node.js | 20+ | 前端 |
| 包管理 | uv | 最新 | Python 依赖 |
| 包管理 | pnpm | 最新 | 前端依赖 |
| 容器 | Docker + Compose | 最新 | 启动 PostgreSQL / Redis |
| 系统依赖 | exiftool | — | EXIF 元数据解析 |
| 系统依赖 | ffmpeg / ffprobe | — | 动态照片视频转码 |

Linux / WSL2 一键安装：

```bash
sudo apt update && sudo apt install -y exiftool ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
npm install -g pnpm
```

---

## 快速开始

```bash
git clone <your-repo-url> ShotMemory
cd ShotMemory
```

`backend/.env` 与 `frontend/.env` 需手动创建（仓库已 gitignore）。

**1. 启动基础设施**

```bash
docker compose up -d
```

首次启动会自动跑 `db-init/`：在 `shotmemory` 库启用 PostGIS 扩展，并创建独立的 `shotmemory_test` 库。

**2. 启动后端 + Worker（两个终端）**

```bash
cd backend
uv sync
uv run alembic upgrade head

# 终端 A
uv run python -m main                          # http://localhost:5683

# 终端 B
uv run arq core.worker.WorkerSettings          # 否则上传后 EXIF/缩略图/视频转码不会触发
```

**3. 启动前端**

```bash
cd frontend
pnpm install
pnpm dev                                       # http://localhost:5173
```

打开 <http://localhost:5173>，注册账号即可开始上传照片。

**4. 运行测试**

```bash
cd backend
uv run pytest                                  # 使用独立的 shotmemory_test 库
```

更多命令（lint / format / 迁移生成 / 压力测试 / pre-commit）见 [`CLAUDE.md`](./CLAUDE.md)。
