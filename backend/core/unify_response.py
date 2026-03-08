from typing import Any, final

import orjson
from fastapi import Response
from pydantic import BaseModel

from core.exceptions import APIStatus


def _orjson_default_fallback(obj: Any) -> Any:
    """
    orjson 序列化 fallback 回调：
    当底层 Rust 引擎遇到无法原生解析的对象（如 Pydantic 模型）时，才会短暂切回 Python 调用此函数。
    """
    if isinstance(obj, BaseModel):
        # ⚠️ 性能核心：不要用 mode="json"！
        # 直接 dump 出原生的 datetime/UUID 等对象，让 orjson 底层的 C/Rust 引擎去极速转字符串
        return obj.model_dump()

    # 防御性编程：严格暴露未知类型，防止静默失败
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@final
class UnifyResponse:
    @classmethod
    def _render(cls, code: int, message: str, data: Any, status_code: int) -> Response:
        """
        内部核心渲染器：接管所有字典构造与极速序列化逻辑，消除冗余代码。
        """
        payload = {
            "code": code,
            "message": message,
            "data": data,  # 直接塞入脏数据（如复杂的嵌套列表、模型等）
        }

        # 使用 orjson 极速转为 bytes
        # option=orjson.OPT_NON_STR_KEYS 允许 payload 中出现整数 key
        json_bytes: bytes = orjson.dumps(
            payload, default=_orjson_default_fallback, option=orjson.OPT_NON_STR_KEYS
        )

        # 返回最底层的 Response，绕过 FastAPI 多余的类型推断与 jsonable_encoder 检查
        return Response(
            content=json_bytes, status_code=status_code, media_type="application/json"
        )

    @classmethod
    def success(
        cls,
        data: Any = None,
        message: str = APIStatus.SUCCESS.msg,
        code: int = APIStatus.SUCCESS.code,
    ) -> Response:
        """
        成功响应
        Args:
            data: 响应数据
            message: 响应消息，默认使用 APIStatus.SUCCESS.msg
            code: 业务状态码，默认使用 APIStatus.SUCCESS.code
        """
        return cls._render(code=code, message=message, data=data, status_code=200)

    @classmethod
    def frontend_error(
        cls,
        code: int = APIStatus.BAD_REQUEST.code,
        message: str = APIStatus.BAD_REQUEST.msg,
        data: Any = None,
        status_code: int = 400,
    ) -> Response:
        """
        前端错误响应
        Args:
            code: 业务错误码 (如 40101)
            message: 错误消息
            data: 额外的错误数据（可选）
            status_code: HTTP 状态码，默认 400
        """
        return cls._render(
            code=code, message=message, data=data, status_code=status_code
        )

    @classmethod
    def backend_error(
        cls, code: int, message: str, data: Any = None, status_code: int = 500
    ) -> Response:
        """
        后端错误响应
        Args:
            code: 业务错误码 (如 40101)
            message: 错误消息
            data: 额外的错误数据（可选）
            status_code: HTTP 状态码，默认 500
        """
        return cls._render(
            code=code, message=message, data=data, status_code=status_code
        )
