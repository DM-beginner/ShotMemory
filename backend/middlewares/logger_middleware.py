import time

import uuid6
from fastapi import Request
from loguru import logger


async def log_requests_middleware(request: Request, call_next):
    # 1. 生成唯一的 Request ID
    request_id = str(uuid6.uuid7())

    # 2. 将 request_id 绑定到当前的上下文 context
    # 之后所有的 logger.info() 都会自动带上这个 request_id
    with logger.contextualize(request_id=request_id):
        start_time = time.time()

        # 记录请求进入
        # 注意：不要记录具体的 body 内容，除非是为了调试，防止敏感信息泄露
        logger.info(f"Started processing request: {request.method} {request.url.path}")

        try:
            # 执行实际请求
            response = await call_next(request)

            process_time = (time.time() - start_time) * 1000  # 毫秒

            # 记录请求结束（包含状态码和耗时）
            logger.info(
                f"Finished processing: status_code={response.status_code} "
                f"time={process_time:.2f}ms"
            )

            # 在响应头中返回 Request-ID，方便前端排查问题
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            # 捕获未处理的异常，记录堆栈
            logger.exception(f"Request failed: {e!s}")
            raise e
