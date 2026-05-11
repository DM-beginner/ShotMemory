# 上生产前清单

当前项目主要在开发环境验证。**真要上生产**需要先把下面这些"已知未做"项处理完。如实记录"未做"是文档的责任——避免未来的你以为"应该有"的东西其实不存在。

---

## 必做项

### 1. AliyunOSSStrategy 实现

**当前状态**：`core/storage/aliyun.py` 所有方法 `raise NotImplementedError`。源码内已注释好实现思路。

**需要做**：
- `uv add oss2`
- 实现 `upload_file` / `upload_bytes` / `delete_file` / `download_to_file`，签名严格遵守 `StorageStrategy`（不要改 interface）。
- 验证 `download_to_file` 在 worker 进程能正常拉文件到临时路径。
- 验证 `lru_cache` 单例在多进程（API + Worker）下各自持有自己的 `Bucket` 实例。

### 2. Cookie 在生产的安全配置

**当前状态**：`COOKIE_SECURE` / `COOKIE_SAMESITE` 由配置注入，dev 默认值不一定适合生产。

**需要做**：
- `COOKIE_SECURE=true`（强制 HTTPS）。
- `COOKIE_SAMESITE=lax` 或 `strict`，取决于是否有跨站调用。
- 配置 `COOKIE_DOMAIN` 为生产域名。
- 验证 refresh_token 的 cookie path `/v1/auth` 在反向代理下仍正确（如 nginx 的 `proxy_cookie_path`）。

### 3. CORS 白名单

**当前状态**：`settings.ORIGINS` 是允许列表，dev 大概率包含 `localhost:5173`。

**需要做**：
- 替换为生产前端域名（精确匹配，不要用 `*`）。
- `allow_credentials=True` + `allow_origins=["*"]` 是不允许的组合，注意。

### 4. 静态文件路由

**当前状态**：`/static` 仅在 `ENV=dev` 下挂载（指向 `backend/uploads/`）。生产 `ENV=prod` 不会挂这个路由。

**需要做**：照片 / 视频 URL 必须由 OSS / CDN 提供。前端 `VITE_STORAGE_BASE_URL` 改为 CDN 域名，不能再指向后端。

---

## 强烈建议项（功能性"未做"）

### 5. 限流（Rate Limiting）

**当前状态**：无。注册 / 登录 / 上传等接口可能被刷。

**建议**：
- 至少给 `/auth/register`、`/auth/login`、`/auth/refresh`、`/photo/uploads` 加 IP 维度限流。
- FastAPI 没有内置，可考虑 `slowapi` 或在反向代理（nginx）层做。

### 6. 密码策略

**当前状态**：长度 6-128，无复杂度要求；无锁定机制；无密码找回。

**建议**：
- 至少加最小复杂度（数字 + 字母）。
- 登录失败次数限制（连续 5 次锁定 15 分钟）。
- 邮箱 / 短信验证码找回密码（涉及邮件 / 短信通道，工作量大，按需）。

### 7. 日志聚合

**当前状态**：日志输出到 stdout/stderr，没有结构化、没有外发。

**建议**：
- 用 `structlog` 之类换成 JSON 输出。
- 接 ELK / Loki / 阿里云日志服务，按级别 / 模块 / trace_id 过滤。

### 8. APM / 监控告警

**当前状态**：无。Worker 卡死、DB 慢查询、API 错误率上升都不会有人知道。

**建议**：
- Sentry（错误聚合，免费 quota 一般够个人项目）。
- Prometheus + Grafana 或阿里云 ARMS（指标）。
- 关键告警：API 5xx 比例、Worker 队列长度、DB 连接池占用率、磁盘使用率。

### 9. 头像上传：去掉 EXIF

**当前状态**：头像走的是 `ImageUtil.generate_thumbnail`，输出 WebP，不会带 EXIF。**已经隐式安全**。但如果未来加"原始头像"功能，要记得显式清 EXIF（GPS 泄露隐私）。

### 10. 备份策略

**当前状态**：无。docker volume 一旦挂载丢失或 `docker compose down -v` 误操作 → 数据全无。

**建议**：
- PostgreSQL 至少每日 `pg_dump` + 异地存储。
- OSS bucket 启用版本控制 + 跨区复制。

---

## 已知技术债（不影响安全但影响维护）

### 11. 测试夹具图片（`backend/tests/test-images/`）不入 git

**症状**：测试用例（`test_uploads.py` / `locustfile.py`）依赖 `backend/tests/test-images/` 目录下的 jpg 样本。该目录体积约 500 MB，已在 `.gitignore` 显式排除，首次 clone 后需手动放图片才能跑测试。

**处理**：详见 [`backend/tests/README.md`](../backend/tests/README.md)。如果后续需要在团队 / CI 间共享一份标准夹具集，建议放对象存储（OSS / S3）+ 提供 fetch 脚本，而非塞进 git。

### 12. `MAX_TRIES=3` 后任务永久丢失

**症状**：worker 任务连续失败 3 次后被 arq 丢弃，无 dead-letter queue。受影响的"孤儿照片"靠人工清。

**处理**：可考虑自定义 arq `keep_result` 或写一个 `failed_jobs` 表持久化失败任务上下文。

### 13. `total` 字段是当前页数量

**症状**：`/v1/photo` 列表的 `total` 实际上是当前页的 `len(items)`，不是真实总数。前端通过 `len(items) == limit` 判断是否有下一页。

**处理**：当前是为了避免 COUNT(*) 慢查询的简化实现。如果未来要做"第 N 页"跳转或展示精确总数，需要补 COUNT 或维护一个估算计数。
