from uuid import UUID

from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.base_model import Base


class StoryPhotoM2M(Base):
    """故事与照片的多对多关联表"""

    __tablename__ = "story_photo_m2m"
    __table_args__ = (
        PrimaryKeyConstraint("story_id", "photo_id"),
        {"schema": "photo_story", "comment": "故事与照片的多对多关联表"},
    )

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("photo_story.story.id", ondelete="CASCADE"),
        primary_key=True,
    )
    photo_id: Mapped[UUID] = mapped_column(
        ForeignKey("photo_story.photo.id", ondelete="CASCADE"),
        primary_key=True,
    )
