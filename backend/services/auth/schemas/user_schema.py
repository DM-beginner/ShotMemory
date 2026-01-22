from pydantic import BaseModel


class RegisterResponseData(BaseModel):
    """注册响应数据"""

    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    created_at: str
