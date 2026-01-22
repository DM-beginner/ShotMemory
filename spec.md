项目名称
ShotMemory

项目愿景
构建一个现代化、高安全性的全栈 Web 应用，专注于用户记忆或日记的存储与管理。系统采用前后端分离架构，强调类型安全（Type Safety）与高性能。

技术栈概览 (Tech Stack)
Frontend (客户端):

核心框架: React 19 + TypeScript (构建于 Vite 之上)

状态管理: Redux Toolkit (RTK) + RTK Query (API 交互)

路由系统: React Router v7

UI 系统: Tailwind CSS v4 + HeroUI + Framer Motion (动画)

工程化: ESLint (Flat Config), pnpm

Backend (服务端):

核心框架: Python 3.13 + FastAPI

运行时: Uvicorn (ASGI) + Gunicorn (进程管理)

包管理: uv (极速 Python 包管理器)

数据库交互: SQLAlchemy (ORM) + Alembic (迁移) + Asyncpg (异步驱动)

认证安全: JWT (RS256/HS256) + Pydantic (数据校验) + Argon2 (密码哈希)

核心架构设计
1. 认证与授权 (Authentication & Authorization) 系统采用了双 Token 轮转机制 (Dual Token Rotation)，这是目前 Web 安全领域的“黄金标准”。

理论模型:

Access Token: 短期有效（30分钟），存储于 HTTPOnly Cookie，用于高频 API 访问。

Refresh Token: 长期有效（7天），存储于 HTTPOnly Cookie（限制路径 /v1/auth），并持久化于数据库，绑定 device_id。

安全策略: 每次刷新 Token 时，会生成新的 Refresh Token（轮转），旧的随即失效。若检测到 Token 盗用，系统可根据 device_id 精确熔断特定设备的会话。

💡 通俗类比：护照与游乐园门票

Refresh Token 就像您的“护照”：它长期有效，非常重要，必须锁在酒店保险箱里（HTTPOnly Cookie），只有在需要换取新门票时才拿出来展示一下。

Access Token 就像“游乐园单日票”：它时效很短，在园区里（API 调用）随时都要挂在胸前给检票员看。

机制优势：如果您的单日票丢了，坏人只能玩几十分钟。而因为您的护照在保险箱里，坏人没法去换明天的票。

2. 后端分层架构 (Layered Architecture) 遵循“关注点分离”原则，采用 DDD（领域驱动设计）的简化版：

Routers (接口层): 处理 HTTP 请求与响应 (auth_router.py)。

Services (业务层): 编排业务逻辑，不直接操作数据库。

Repos (仓储层): 封装数据库原子操作 (user_repo.py)。

Models/Schemas: 定义数据结构与传输对象。

3. 错误处理 (Unified Error Handling)

通过 UnifyResponse 和 BusinessException 实现了全局统一的响应格式。

所有业务异常（如“用户不存在”、“密码错误”）均有唯一的 code 标识，便于前端国际化与排错。

！！！注意：请不要使用旧版本的语法
