"""
auth 服务专属业务异常类
继承自 core.exceptions.BaseError，由全局 exception_handler 统一捕获处理
"""

from core.exceptions import APIStatus, BaseError


class AuthError(BaseError):
    """认证相关异常"""

    def __init__(
        self,
        code: int = APIStatus.UNAUTHORIZED.code,
        message: str = APIStatus.UNAUTHORIZED.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=401)


class UserError(BaseError):
    """用户相关异常"""

    def __init__(
        self,
        code: int = APIStatus.USER_NOT_FOUND.code,
        message: str = APIStatus.USER_NOT_FOUND.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=400)


class TokenError(BaseError):
    """Token 相关异常"""

    def __init__(
        self,
        code: int = APIStatus.TOKEN_INVALID.code,
        message: str = APIStatus.TOKEN_INVALID.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=401)
