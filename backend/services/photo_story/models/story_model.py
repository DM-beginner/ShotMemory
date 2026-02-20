from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base, CreatedTimeMixin, IDMixin, UpdatedTimeMixin
from services.photo_story.models import StoryPhotoM2M

if TYPE_CHECKING:
    from services.photo_story.models.photo_model import Photo


class Story(Base, IDMixin, CreatedTimeMixin, UpdatedTimeMixin):
    """故事表：用户创建的图文故事"""

    __tablename__ = "story"
    __table_args__ = (
        # 为常用查询字段添加索引
        Index("ix_story_user_id", "user_id"),
        Index("ix_story_created_at", "created_at"),
        {
            "schema": "photo_story",
            "comment": "故事表，存储用户创作的图文故事内容",
        },
    )

    # 关联用户
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("auth.user.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属用户ID",
    )

    # 故事内容
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="故事标题")
    content: Mapped[str | None] = mapped_column(
        Text, comment="故事内容（Markdown/富文本）"
    )

    # 封面图（用于瀑布流展示）
    cover_photo_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("photo_story.photo.id", ondelete="SET NULL"),
        comment="封面照片ID",
    )

    # 时间字段由 CreatedTimeMixin 和 UpdatedTimeMixin 提供

    # 关系定义：一个故事对应多张照片
    photos: Mapped[list["Photo"]] = relationship(
        "Photo",
        secondary=StoryPhotoM2M.__table__,  # 重点：指定中间表
        back_populates="stories",
        lazy="select",
    )

    # 封面照片关系（单独定义，避免循环引用）
    cover_photo: Mapped["Photo | None"] = relationship(
        "Photo",
        foreign_keys=[cover_photo_id],
        lazy="select",
        post_update=True,  # 解决循环外键问题
    )
