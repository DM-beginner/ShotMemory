from enum import Enum


class APIStatus(Enum):
    """
    业务状态码枚举类
    格式：(code, message)
    """

    # --- 20000: 成功 ---
    SUCCESS = (20000, "操作成功")

    # --- 400xx: 通用客户端错误 ---
    BAD_REQUEST = (40000, "请求参数错误")
    UNAUTHORIZED = (40001, "未授权或Token失效")
    FORBIDDEN = (40003, "无权限访问")
    NOT_FOUND = (40004, "请求资源不存在")

    # --- 401xx: 用户/认证模块 ---
    USER_NOT_FOUND = (40101, "用户不存在")
    USER_PASSWORD_ERROR = (40102, "用户名或密码错误")
    USER_EXISTS = (40103, "用户已存在")
    USER_LOCKED = (40104, "用户已被冻结")
    USER_DELETED = (40105, "用户已被删除")
    EMAIL_EXISTS = (40106, "邮箱已存在")

    # --- 402xx: 业务逻辑错误 (例如 RefreshToken) ---
    TOKEN_INVALID = (40201, "Refresh Token 不存在或已失效")
    TOKEN_REVOKED = (40202, "Refresh Token 已被废弃")
    TOKEN_EXPIRED = (40203, "Refresh Token 已过期")
    TOKEN_NOT_PROVIDED = (40204, "Refresh Token 未提供")
    TOKEN_TYPE_ERROR = (40205, "Token 类型错误")

    # --- 500xx: 服务端错误 ---
    SYSTEM_ERROR = (50000, "系统内部错误")
    DB_ERROR = (50001, "数据库操作异常")
    THIRD_PARTY_ERROR = (50002, "第三方服务调用失败")

    @property
    def code(self):
        """获取状态码"""
        return self.value[0]

    @property
    def msg(self):
        """获取提示信息"""
        return self.value[1]
