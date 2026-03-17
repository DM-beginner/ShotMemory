from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import inspect as sa_inspect

from services.photo_story.schemas.photo_schema import (
    PhotoResponse,
    derive_thumbnail_key,
)


class StoryCreateRequest(BaseModel):
    """创建故事的请求"""

    title: str = Field(description="故事标题", min_length=1, max_length=255)
    content: str | None = Field(default=None, description="故事内容（Markdown）")
    cover_photo_id: UUID | None = Field(default=None, description="封面照片ID")
    photo_ids: list[UUID] = Field(
        default_factory=list, description="关联的照片ID列表", max_length=9
    )


class StoryUpdateRequest(BaseModel):
    """更新故事的请求"""

    title: str | None = Field(
        default=None, description="故事标题", min_length=1, max_length=255
    )
    content: str | None = Field(default=None, description="故事内容（Markdown）")
    cover_photo_id: UUID | None = Field(default=None, description="封面照片ID")
    photo_ids: list[UUID] | None = Field(
        default=None, description="关联的照片ID列表（None=不更新）", max_length=9
    )


class StoryResponse(BaseModel):
    """故事信息响应（不含照片列表）"""

    id: UUID = Field(description="故事ID")
    user_id: UUID = Field(description="所属用户ID")
    title: str = Field(description="故事标题")
    content: str | None = Field(description="故事内容")
    cover_photo_id: UUID | None = Field(description="封面照片ID")
    cover_thumbnail_key: str | None = Field(
        default=None, description="封面缩略图路径"
    )
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def derive_cover_thumbnail(cls, data: Any) -> Any:
        """从 cover_photo ORM 关系推导封面缩略图路径"""
        if not isinstance(data, dict):
            # ORM 对象：推导 cover_thumbnail_key
            cover_photo = getattr(data, "cover_photo", None)
            cover_thumbnail_key = None
            if cover_photo and getattr(cover_photo, "exif_data", None) is not None:
                object_key = getattr(cover_photo, "object_key", None)
                if object_key:
                    cover_thumbnail_key = derive_thumbnail_key(object_key)

            result = {
                "id": data.id,
                "user_id": data.user_id,
                "title": data.title,
                "content": data.content,
                "cover_photo_id": data.cover_photo_id,
                "cover_thumbnail_key": cover_thumbnail_key,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
            # 传递 photos 属性（StoryDetailResponse 需要），仅在已加载时访问
            if "photos" not in sa_inspect(data).unloaded:
                result["photos"] = data.photos
            return result
        return data


class StoryDetailResponse(StoryResponse):
    """故事详情响应（含照片列表，已按 sort_order 排序）"""

    photos: list[PhotoResponse] = Field(description="关联的照片列表")


class StoryListResponse(BaseModel):
    """故事列表响应"""

    total: int = Field(description="总数量")
    items: list[StoryResponse] = Field(description="故事列表")
