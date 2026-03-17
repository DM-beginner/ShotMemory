from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.photo_story.models import Photo, PhotoStoryM2M, Story


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
        """根据 ID 获取故事，with_photos=True 时同时加载 photos 和 cover_photo"""
        query = select(Story).where(Story.id == story_id)

        if with_photos:
            query = query.options(
                selectinload(Story.photos),
                selectinload(Story.cover_photo),
            )
        else:
            query = query.options(selectinload(Story.cover_photo))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_list_with_cover(
        cls,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Story], int]:
        """获取用户故事列表 + 总数，预加载 cover_photo"""
        # 总数查询
        count_query = select(func.count(Story.id)).where(Story.user_id == user_id)
        total = (await db.execute(count_query)).scalar_one()

        # 列表查询
        query = (
            select(Story)
            .where(Story.user_id == user_id)
            .options(selectinload(Story.cover_photo))
            .order_by(Story.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        stories = list(result.scalars().all())

        return stories, total

    @classmethod
    async def update(cls, db: AsyncSession, story: Story) -> Story:
        """更新故事记录"""
        await db.commit()
        await db.refresh(story, attribute_names=["cover_photo"])
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
    async def replace_photos(
        cls, db: AsyncSession, story_id: UUID, photo_ids: list[UUID]
    ) -> None:
        """替换故事的照片关联：DELETE 旧关联 → batch INSERT 新关联（含 sort_order）"""
        # 删除旧关联
        await db.execute(
            delete(PhotoStoryM2M).where(PhotoStoryM2M.story_id == story_id)
        )

        # 批量插入新关联
        if photo_ids:
            await db.execute(
                PhotoStoryM2M.__table__.insert(),
                [
                    {"story_id": story_id, "photo_id": pid, "sort_order": idx}
                    for idx, pid in enumerate(photo_ids)
                ],
            )

    @classmethod
    async def batch_validate_photo_ownership(
        cls, db: AsyncSession, photo_ids: list[UUID], user_id: UUID
    ) -> set[UUID]:
        """批量验证照片归属，返回属于该用户的照片 ID 集合"""
        if not photo_ids:
            return set()
        result = await db.execute(
            select(Photo.id).where(Photo.id.in_(photo_ids), Photo.user_id == user_id)
        )
        return set(result.scalars().all())
