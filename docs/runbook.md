# Runbook — 故障与运维手册

只覆盖**当前真实存在**的故障路径和应急操作。猜测性场景（如"Sentry 告警 X 触发后..."）不写。

---

## 启动顺序

正常启动顺序：**PostgreSQL + Redis（容器） → 后端 API → arq Worker → 前端**。Worker 必须在主服务之后或并行启动；否则上传后照片会一直停在 `processing` 状态。

```bash
docker compose up -d                                 # 1. 基础设施
cd backend && uv run python -m main                  # 2. API（终端 A）
cd backend && uv run arq core.worker.WorkerSettings  # 3. Worker（终端 B）
cd frontend && pnpm dev                              # 4. 前端
```

---

## Worker 处理卡住 / 队列堆积

**症状**：上传照片后 `GET /v1/photo/{id}` 长时间 `status=="processing"`，缩略图永远不出现。

**排查**：

1. 确认 Worker 进程在跑：`ps aux | grep arq`。
2. 看 Worker 日志：terminal B 里有没有 traceback？常见原因：
   - exiftool / ffmpeg 没装（`apt install exiftool ffmpeg`）。
   - 单个任务超过 `job_timeout=120s`（视频太大 / ffmpeg 卡）。
   - 数据库连接池耗尽（应该不会，Worker 池只有 5+5）。
3. 看 Redis 队列堆积：`docker exec shotmemory_redis redis-cli -n 1 KEYS "arq:queue*"`。
4. 强行重启 Worker：Ctrl+C 后重启即可，未完成任务会留在队列里被重新拉取。

**恢复**：受影响照片若 `exif_data` 还是 NULL，重启 Worker 后会被重新处理（前提是任务还在 Redis DB1 里）。如果任务已经因 `max_tries=3` 全部失败被丢弃，需要手动清理这些"孤儿照片"——直接删除即可（前端按 status 显示 processing 的卡片体验差，不如重传）。

---

## Redis 挂了

**主服务影响**：

- 缓存层（DB0）：所有依赖缓存的接口需走数据库降级（如果业务层使用了缓存的话；目前少）。
- 任务队列（DB1）：`arq_redis.enqueue_job` 抛错 → 上传接口因为在 `try` 内会触发 catch all 反向清理 → 用户收到 `50000`。

**Worker 影响**：完全不工作（Redis 是 broker）。

**恢复**：`docker compose restart shotmemory_redis`。重启后已上传但未投递的任务**永久丢失**——需要手动清理对应"孤儿照片"或重传。**注**：DB0 是缓存，丢失无影响；DB1 是队列，丢失即任务丢失（arq 默认无持久化策略）。

---

## DB 迁移回滚

```bash
cd backend
uv run alembic downgrade -1                # 回滚一个版本
uv run alembic downgrade <revision_hash>   # 回滚到指定版本
uv run alembic history                     # 看迁移历史
```

**安全约束**：

- 不可回滚的迁移类型：DROP COLUMN、DROP TABLE、不可逆的数据迁移、修改字段类型导致数据丢失的。
- 写迁移时要写 `downgrade()` 函数；自动生成的迁移文件 `downgrade()` 经常是空的或不完整，**人工 review 必须做**。
- 部分唯一索引、PostGIS 扩展启用这类操作的 downgrade 要单独验证。

---

## 上传失败定位

接口返回 `50000` 时按以下顺序排查：

1. **Storage 层**（Local）：检查 `backend/uploads/originals/` 是否可写、磁盘是否满。
2. **DB 写入**：看 API 日志有无 `IntegrityError` / `OperationalError`。
3. **enqueue 失败**：看日志有无 `redis.ConnectionError`。

上传过程已自动反向清理（见 `docs/flows/photo-upload-flow.md`），不会留下孤儿文件。

**孤儿文件清理**：当前没有定时清理脚本。如果 OSS 异步删除（worker `delete_oss_files`）反复失败被 arq 丢弃，会留下孤儿——只能人工清。后续若需要可加定时任务比对 DB 与 OSS。

---

## 健康检查

| 服务 | 检查命令 |
|------|---------|
| API | `curl http://localhost:5683/v1/health` |
| Postgres | `docker exec shotmemory_postgres pg_isready` |
| Redis | `docker exec shotmemory_redis redis-cli ping` |
| Worker | `ps aux | grep arq` 或看 terminal B 是否有 `arq.worker - INFO` 心跳 |

---

## 完全重置开发环境

```bash
docker compose down -v          # 销毁数据卷（DB + Redis 数据全丢）
docker compose up -d            # 重新拉起，db-init 脚本会自动跑
cd backend
uv run alembic upgrade head     # 重建 schema
```

注意 `down -v` 会清掉所有照片数据（DB 记录 + Redis 队列），但**不会**清掉 `backend/uploads/` 下的本地文件——那是 Bind 之外的路径。如果要全干净：`rm -rf backend/uploads/{originals,thumbnails,videos}/*`。
