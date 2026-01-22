from pydantic import BaseModel, Field


class BaseResponse[T](BaseModel):
    """
    统一响应模型，用于生成 OpenAPI 文档
    """

    code: int = Field(default=2000, description="业务状态码，2000表示成功")
    message: str = Field(default="Success", description="响应信息")
    data: T | None = Field(default=None, description="业务数据")

    # 允许通过 Config 配置来兼容 ORM 对象
    class Config:
        from_attributes = True
