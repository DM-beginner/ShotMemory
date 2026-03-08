import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from geoalchemy2 import Geometry, WKBElement  # PostGIS 支持
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base, CreatedTimeMixin, IDMixin
from services.photo_story.models.story_photo_m2m import PhotoStoryM2M

if TYPE_CHECKING:
    from services.photo_story.models.story_model import Story


class Photo(Base, IDMixin, CreatedTimeMixin):
    """照片表：存储用户上传的照片及元数据"""

    __tablename__ = "photo"
    __table_args__ = (
        # 为常用查询字段添加索引
        Index("ix_photo_user_id", "user_id"),
        Index("ix_photo_object_key", "object_key"),
        Index("ix_photo_taken_at", "taken_at"),
        {
            "schema": "photo_story",
            "comment": "照片表，存储照片文件路径、尺寸、地理位置、EXIF 等元数据",
        },
    )

    # 关联用户
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth.user.id", ondelete="CASCADE"),
        comment="所属用户ID",
    )

    # 核心字段：只存相对路径（如 2024/01/xxx.jpg）
    object_key: Mapped[str] = mapped_column(String(500), comment="OSS中的相对路径")

    # 缩略图访问 URL（WebP 格式，上传时由后端生成）
    thumbnail_key: Mapped[str | None] = mapped_column(
        String(500), comment="OSS中的缩略图相对路径"
    )

    # 图片尺寸：宽高分离，方便前端计算纵横比
    width: Mapped[int | None] = mapped_column(Integer, comment="图片宽度(px)")
    height: Mapped[int | None] = mapped_column(Integer, comment="图片高度(px)")

    # PostGIS 地理位置（SRID 4326 是最通用的经纬度格式：WGS84）从v。k/'l.（关闭自带的空间索引，交给 Alembic 管理）
    location_wkt: Mapped[WKBElement | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False), comment="拍摄地点经纬度"
    )

    # EXIF 数据（完整的元数据，JSON 格式）
    exif_data: Mapped[dict | None] = mapped_column(JSONB, comment="完整的EXIF元数据")

    # 时间字段
    taken_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="拍摄时间（从EXIF提取）",
    )
    # created_at 由 CreatedTimeMixin 提供（上传时间）

    # 关系定义
    stories: Mapped[list["Story"]] = relationship(
        "Story",
        secondary=PhotoStoryM2M.__table__,  # 重点：指定中间表
        back_populates="photos",
        lazy="selectin",
    )
