import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# 登录请求体
class LoginRequest(BaseModel):
    """
    登录请求：支持邮箱或手机号登录
    - 必须提供 email 或 phone 其中之一
    """

    email: EmailStr | None = Field(None, description="邮箱")
    phone: str | None = Field(None, description="手机号")
    password: str = Field(..., description="密码")
    device_id: UUID = Field(..., description="设备唯一标识，前端生成并持久化存储")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """验证手机号格式（中国大陆）"""
        if v is not None and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v

    @model_validator(mode="after")
    def check_email_or_phone(self) -> "LoginRequest":
        """确保至少提供 email 或 phone"""
        if not self.email and not self.phone:
            raise ValueError("请提供邮箱或手机号")
        return self


# 注册请求体
class RegisterRequest(BaseModel):
    """
    注册请求：支持邮箱或手机号注册
    - 必须提供 email 或 phone 其中之一
    """

    name: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: EmailStr | None = Field(None, description="邮箱")
    phone: str | None = Field(None, description="手机号")
    password: str = Field(..., min_length=6, max_length=128, description="密码")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """验证手机号格式（中国大陆）"""
        if v is not None and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v

    @model_validator(mode="after")
    def check_email_or_phone(self) -> "RegisterRequest":
        """确保至少提供 email 或 phone"""
        if not self.email and not self.phone:
            raise ValueError("请提供邮箱或手机号")
        return self


# Token Payload 解析结果
class TokenPayload(BaseModel):
    sub: str  # JWT 中 sub 是字符串形式的 UUID（user_id）
    type: str  # JWT 中 type 是 token 类型（access 或 refresh）


# 认证响应数据
class AuthResponseData(BaseModel):
    """认证接口的响应数据"""

    message: str
    token_type: str = "bearer"


# OAuth2 Token 响应（Swagger UI 标准格式）
class OAuth2TokenResponse(BaseModel):
    """OAuth2 标准 Token 响应"""

    access_token: str
    token_type: str = "bearer"
