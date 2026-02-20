from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.photo_story.models import Photo, StoryPhotoM2M


class PhotoRepo:
    """Photo 表的 CRUD 操作仓库"""

    @classmethod
    async def create(cls, db: AsyncSession, photo: Photo) -> Photo:
        """创建照片记录"""
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        return photo

    @classmethod
    async def get_by_id(cls, db: AsyncSession, photo_id: UUID) -> Photo | None:
        """根据 ID 获取照片"""
        result = await db.execute(select(Photo).where(Photo.id == photo_id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_user_id(
        cls, db: AsyncSession, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[Photo]:
        """获取用户的照片列表（分页）"""
        result = await db.execute(
            select(Photo)
            .where(Photo.user_id == user_id)
            .order_by(Photo.taken_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @classmethod
    async def get_by_story_id(cls, db: AsyncSession, story_id: UUID) -> list[Photo]:
        """获取故事的所有照片（通过 M2M 表联查）"""
        result = await db.execute(
            select(Photo)
            .join(
                StoryPhotoM2M.__table__, Photo.id == StoryPhotoM2M.__table__.c.photo_id
            )
            .where(StoryPhotoM2M.__table__.c.story_id == story_id)
            .order_by(Photo.taken_at.asc())
        )
        return list(result.scalars().all())

    @classmethod
    async def update(cls, db: AsyncSession, photo: Photo) -> Photo:
        """更新照片记录"""
        await db.commit()
        await db.refresh(photo)
        return photo

    @classmethod
    async def delete(cls, db: AsyncSession, photo_id: UUID) -> bool:
        """删除照片记录"""
        photo = await cls.get_by_id(db, photo_id)
        if not photo:
            return False
        await db.delete(photo)
        await db.commit()
        return True

    @classmethod
    async def get_orphan_photos(
        cls, db: AsyncSession, user_id: UUID, limit: int = 50
    ) -> list[Photo]:
        """获取未关联故事的照片（孤儿照片）- 通过 M2M 表反查"""
        # 子查询：所有已关联故事的照片 ID
        subquery = select(StoryPhotoM2M.__table__.c.photo_id).subquery()

        result = await db.execute(
            select(Photo)
            .where(Photo.user_id == user_id, Photo.id.not_in(subquery))
            .order_by(Photo.taken_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
