"""replace thumbnail_key and video_key with has_video

Revision ID: a1b2c3d4e5f6
Revises: f225db269af0
Create Date: 2026-03-15 05:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f225db269af0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add has_video, migrate data, drop thumbnail_key and video_key."""
    # 1. 新增 has_video 列（带 server_default 避免 NOT NULL 约束冲突）
    op.add_column(
        "photo",
        sa.Column(
            "has_video",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="是否有关联视频",
        ),
        schema="photo_story",
    )

    # 2. 数据迁移：将原有 video_key 的信息转移到 has_video
    op.execute(
        "UPDATE photo_story.photo SET has_video = true WHERE video_key IS NOT NULL"
    )

    # 3. 删除旧列
    op.drop_column("photo", "thumbnail_key", schema="photo_story")
    op.drop_column("photo", "video_key", schema="photo_story")


def downgrade() -> None:
    """Restore thumbnail_key and video_key columns."""
    op.add_column(
        "photo",
        sa.Column(
            "video_key",
            sa.String(length=500),
            nullable=True,
            comment="动态照片/实况照片的视频文件路径",
        ),
        schema="photo_story",
    )
    op.add_column(
        "photo",
        sa.Column(
            "thumbnail_key",
            sa.String(length=500),
            nullable=True,
            comment="OSS中的缩略图相对路径",
        ),
        schema="photo_story",
    )
    op.drop_column("photo", "has_video", schema="photo_story")
