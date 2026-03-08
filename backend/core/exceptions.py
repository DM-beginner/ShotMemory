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

    # --- 403xx: 文件/存储模块 ---
    FILE_UPLOAD_FAILED = (40301, "文件上传失败")
    FILE_NOT_FOUND = (40302, "文件不存在")
    FILE_DELETE_FAILED = (40303, "文件删除失败")
    FILE_TYPE_NOT_ALLOWED = (40304, "不支持的文件类型")
    FILE_TOO_LARGE = (40305, "文件大小超出限制")

    # --- 404xx: 照片/故事模块 ---
    PHOTO_NOT_FOUND = (40401, "照片不存在")
    PHOTO_ACCESS_DENIED = (40402, "无权访问该照片")
    PHOTO_PROCESSING_FAILED = (40403, "照片处理失败")
    STORY_NOT_FOUND = (40404, "故事不存在")
    STORY_ACCESS_DENIED = (40405, "无权访问该故事")
    STORY_PHOTO_ALREADY_EXISTS = (40406, "照片已在故事中")
    STORY_PHOTO_NOT_FOUND = (40407, "照片不在该故事中")
    THUMBNAIL_GENERATION_FAILED = (40408, "缩略图生成失败")

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

class BaseError(Exception):
    """基础异常"""

    def __init__(
        self,
        code: int = APIStatus.BAD_REQUEST.code,
        message: str = APIStatus.BAD_REQUEST.msg,
        data: dict | None = None,
        status_code: int = 400,
    ):
        super().__init__(code=code, message=message, data=data, status_code=status_code)