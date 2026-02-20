from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.photo_story.models import Story


class StoryRepo:
    """Story 表的 CRUD 操作仓库"""

    @classmethod
    async def create(cls, db: AsyncSession, story: Story) -> Story:
        """创建故事记录"""
        db.add(story)
        await db.commit()
        await db.refresh(story)
        return story

    @classmethod
    async def get_by_id(
        cls, db: AsyncSession, story_id: UUID, with_photos: bool = False
    ) -> Story | None:
        """根据 ID 获取故事"""
        query = select(Story).where(Story.id == story_id)

        if with_photos:
            # 预加载关联的照片，避免 N+1 查询
            query = query.options(selectinload(Story.photos))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_user_id(
        cls,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        with_photos: bool = False,
    ) -> list[Story]:
        """获取用户的故事列表（分页）"""
        query = (
            select(Story)
            .where(Story.user_id == user_id)
            .order_by(Story.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if with_photos:
            query = query.options(selectinload(Story.photos))

        result = await db.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def update(cls, db: AsyncSession, story: Story) -> Story:
        """更新故事记录"""
        await db.commit()
        await db.refresh(story)
        return story

    @classmethod
    async def delete(cls, db: AsyncSession, story_id: UUID) -> bool:
        """删除故事记录"""
        story = await cls.get_by_id(db, story_id)
        if not story:
            return False
        await db.delete(story)
        await db.commit()
        return True

    @classmethod
    async def count_by_user_id(cls, db: AsyncSession, user_id: UUID) -> int:
        """统计用户的故事数量"""
        result = await db.execute(
            select(func.count(Story.id)).where(Story.user_id == user_id)
        )
        return result.scalar_one()
