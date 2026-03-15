from pydantic import BaseModel


class RegisterResponseData(BaseModel):
    """注册响应数据"""

    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    created_at: str


class MeResponseData(BaseModel):
    """当前登录用户信息"""

    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    avatar_key: str | None = None
