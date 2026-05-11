# AI Agent 开发规范

本项目使用 Claude Code 管理，所有编码规范和架构决策已写入以下文件：

- 项目总览与开发命令：[CLAUDE.md](./CLAUDE.md)
- 后端架构：[docs/architecture.md](./docs/architecture.md)
- 前端架构：[docs/frontend-architecture.md](./docs/frontend-architecture.md)
- 模块设计：[docs/modules/](./docs/modules/)
- 跨模块流程：[docs/flows/](./docs/flows/)

请在开始编码前阅读 `CLAUDE.md`，遵循其中的规范。修改任何模块前，先阅读对应的 `docs/modules/*.md`（auth / photo / story / storage / worker），并在改动跨模块逻辑（例如照片上传链路）时同步参考 `docs/flows/`。
