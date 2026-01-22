"""
自定义业务异常类
用于在业务逻辑中抛出，由 exception_handler 统一捕获并转换为 UnifyResponse 格式
"""

from core.base_code import APIStatus


class BusinessError(Exception):
    """
    业务逻辑异常基类
    用于抛出业务层的错误，由 exception_handler 统一处理
    """

    def __init__(
        self,
        code: int = APIStatus.BAD_REQUEST.code,
        message: str = APIStatus.BAD_REQUEST.msg,
        data: dict | None = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.data = data
        self.status_code = status_code
        super().__init__(self.message)


class AuthError(BusinessError):
    """认证相关异常"""

    def __init__(
        self,
        code: int = APIStatus.UNAUTHORIZED.code,
        message: str = APIStatus.UNAUTHORIZED.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=401)


class UserError(BusinessError):
    """用户相关异常"""

    def __init__(
        self,
        code: int = APIStatus.USER_NOT_FOUND.code,
        message: str = APIStatus.USER_NOT_FOUND.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=400)


class TokenError(BusinessError):
    """Token 相关异常"""

    def __init__(
        self,
        code: int = APIStatus.TOKEN_INVALID.code,
        message: str = APIStatus.TOKEN_INVALID.msg,
        data: dict | None = None,
    ):
        super().__init__(code=code, message=message, data=data, status_code=401)
