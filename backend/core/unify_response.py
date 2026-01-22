from typing import Any

from fastapi.responses import ORJSONResponse

from core.base_code import APIStatus


class UnifyResponse:
    @classmethod
    def success(
        cls,
        data: Any = None,
        message: str = APIStatus.SUCCESS.msg,
        code: int = APIStatus.SUCCESS.code,
    ):
        """
        成功响应
        Args:
            data: 响应数据
            message: 响应消息，默认使用 APIStatus.SUCCESS.msg
            code: 业务状态码，默认使用 APIStatus.SUCCESS.code
        """
        return ORJSONResponse(
            status_code=200,
            content={
                "code": code,
                "message": message,
                "data": data,
            },
        )

    @classmethod
    def frontend_error(
        cls,
        code: int = APIStatus.BAD_REQUEST.code,
        message: str = APIStatus.BAD_REQUEST.msg,
        data: Any = None,
        status_code: int = 400,
    ):
        """
        错误响应
        Args:
            code: 业务错误码 (如 40101)
            message: 错误消息
            data: 额外的错误数据（可选）
            status_code: HTTP 状态码，默认 400
        """
        return ORJSONResponse(
            status_code=status_code,
            content={
                "code": code,
                "message": message,
                "data": data,
            },
        )

    @classmethod
    def backend_error(
        cls, code: int, message: str, data: Any = None, status_code: int = 500
    ):
        """
        错误响应
        Args:
            code: 业务错误码 (如 40101)
            message: 错误消息
            data: 额外的错误数据（可选）
            status_code: HTTP 状态码，默认 500
        """
        return ORJSONResponse(
            status_code=status_code,
            content={
                "code": code,
                "message": message,
                "data": data,
            },
        )
