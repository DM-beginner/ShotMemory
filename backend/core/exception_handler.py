import traceback

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from loguru import logger

from core.base_code import APIStatus
from core.config import settings
from core.custom_exception import BusinessError
from core.unify_response import UnifyResponse


async def business_error_handler(
    request: Request, exc: BusinessError
) -> ORJSONResponse:
    """
    处理业务逻辑异常（自定义的 BusinessError）
    这是我们主动抛出的可预期的业务错误
    """
    logger.info(
        f"BusinessError: {exc.code} - {exc.message} | "
        f"Path: {request.method} {request.url.path}"
    )
    return UnifyResponse.frontend_error(
        code=exc.code, message=exc.message, data=exc.data, status_code=exc.status_code
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> ORJSONResponse:
    """
    处理 FastAPI 的 HTTPException
    通常是框架层面的错误（如 404, 405 等）
    """
    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail} | "
        f"Path: {request.method} {request.url.path}"
    )

    # 根据 HTTP 状态码映射到业务状态码
    status_map = {
        401: APIStatus.UNAUTHORIZED,
        403: APIStatus.FORBIDDEN,
        404: APIStatus.NOT_FOUND,
    }
    api_status = status_map.get(exc.status_code, APIStatus.BAD_REQUEST)

    return UnifyResponse.frontend_error(
        code=api_status.code,
        message=exc.detail or api_status.msg,
        status_code=exc.status_code,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> ORJSONResponse:
    """
    处理请求参数验证错误（Pydantic）
    当请求参数不符合 Schema 定义时触发
    """
    errors = exc.errors()
    logger.warning(
        f"Validation error: {errors} | Path: {request.method} {request.url.path}"
    )

    # 格式化验证错误信息
    error_messages = []
    for error in errors:
        loc = " -> ".join(str(x) for x in error["loc"])
        error_messages.append(f"{loc}: {error['msg']}")

    return UnifyResponse.frontend_error(
        code=APIStatus.BAD_REQUEST.code,
        message="请求参数验证失败",
        data={"details": error_messages},
        status_code=400,
    )


async def general_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    """
    处理所有未捕获的异常
    这些是不可预期的系统错误（如代码 bug、数据库崩溃等）
    """
    # 记录完整的堆栈信息
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc!s} | "
        f"Path: {request.method} {request.url.path}\n"
        f"Traceback: {traceback.format_exc()}"
    )

    return UnifyResponse.backend_error(
        code=APIStatus.SYSTEM_ERROR.code,
        message="服务器内部错误" if settings.ENV == "prod" else str(exc),
        data={"traceback": traceback.format_exc()} if settings.ENV == "dev" else None,
        status_code=500,
    )
