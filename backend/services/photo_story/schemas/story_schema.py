from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from services.photo_story.schemas.photo_schema import PhotoResponse


class StoryCreateRequest(BaseModel):
    """创建故事的请求"""

    title: str = Field(description="故事标题", min_length=1, max_length=255)
    content: str | None = Field(default=None, description="故事内容（Markdown）")
    cover_photo_id: UUID | None = Field(default=None, description="封面照片ID")
    photo_ids: list[UUID] | None = Field(default=None, description="关联的照片ID列表")


class StoryUpdateRequest(BaseModel):
    """更新故事的请求"""

    title: str | None = Field(
        default=None, description="故事标题", min_length=1, max_length=255
    )
    content: str | None = Field(default=None, description="故事内容（Markdown）")
    cover_photo_id: UUID | None = Field(default=None, description="封面照片ID")


class StoryResponse(BaseModel):
    """故事信息响应（不含照片列表）"""

    id: UUID = Field(description="故事ID")
    user_id: UUID = Field(description="所属用户ID")
    title: str = Field(description="故事标题")
    content: str | None = Field(description="故事内容")
    cover_photo_id: UUID | None = Field(description="封面照片ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    model_config = {"from_attributes": True}


class StoryDetailResponse(StoryResponse):
    """故事详情响应（含照片列表）"""

    photos: list[PhotoResponse] = Field(description="关联的照片列表")


class StoryListResponse(BaseModel):
    """故事列表响应"""

    total: int = Field(description="总数量")
    items: list[StoryResponse] = Field(description="故事列表")
