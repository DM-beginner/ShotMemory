# Tests

后端测试代码，运行在独立的 `shotmemory_test` 库（首次启动 Docker 时由 `db-init/init-test-db.sql` 自动创建）。

## 运行

```bash
cd backend
uv run pytest                                            # 全量
uv run pytest tests/test_uploads.py                      # 单文件
uv run pytest tests/test_concurrent.py::test_xxx -v      # 单用例
uv run pytest -s                                         # 看打印
```

压力测试：

```bash
uv run locust -f tests/locustfile.py --host=http://localhost:5683
```

## 测试夹具图片（`test-images/`）

**该目录不入 git**（图片总体积约 500 MB，进仓库会让 clone 不可接受）。`.gitignore` 已显式排除。

测试用例（`test_uploads.py` / `locustfile.py`）通过 `Path(__file__).parent / "test-images"` 引用本目录，期望里面有若干 `.jpg` 文件。

**首次跑测试前需要手动放图片**：

- 任意从手机相册拷出 5-10 张 jpg 即可，文件名不限。
- 想测 Live Photo / Motion Photo 配对，分别放对应格式的样本。
- 想测 EXIF GPS、视频转码等特殊路径，挑带对应元数据的样本。

如果以后需要在团队 / CI 间共享一份标准夹具集，建议放对象存储（OSS / S3）并写个 fetch 脚本，而非塞进 git。

## conftest 设计要点

- session 级 fixture 一次性建表 / 测完 drop schema
- 每个 HTTP 用例使用独立 `AsyncClient` + 独立 `AsyncSession`
- 真实连接 Redis（不 mock），arq 任务真实入队
- `authed_client` fixture 自动注册 + 登录，cookie 已就绪
