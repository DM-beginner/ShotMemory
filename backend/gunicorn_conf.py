import multiprocessing

# 1. 动态计算 Worker 数量
workers = multiprocessing.cpu_count() * 2 + 1

# 2. 指定 Worker 类型
worker_class = "uvicorn.workers.UvicornWorker"

# 3. 绑定地址
bind = "0.0.0.0:9000"

# 4. 内存泄漏防护：处理多少请求后重启
max_requests = 2000
max_requests_jitter = 400

# 5. 超时设置 (秒)
# FastAPI 某些慢接口可能需要更长时间，默认 30s 可能不够
timeout = 60
keepalive = 5

# 6. 日志配置 (配合 Docker 使用)
# 生产环境通常把日志输出到标准输出，由 Docker/K8s 收集
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 7. 进程名称 (方便 htop 查看)
proc_name = "fastapi_app"

# 启动命令
# gunicorn -c gunicorn_conf.py app_loader:app
