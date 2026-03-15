from typing import Any
from uuid import UUID

from geoalchemy2 import WKTElement
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.photo_story.models import Photo, PhotoStoryM2M
from services.photo_story.schemas.photo_schema import PhotoWorkerUpdate


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
    async def create_many(
        cls, db: AsyncSession, photo_dicts: list[dict[str, Any]]
    ) -> list[Photo]:
        """
        原生 Core 风格的高性能批量插入。

        优势：性能极致，完全绕过 ORM 状态追踪的开销；支持一次性 RETURNING 返回带自增主键的完整对象。
        劣势：传入的不再是 ORM 实例，而是纯字典列表。
        """
        if not photo_dicts:
            return []

        # 构造批量插入语句，并要求数据库返回插入后的完整行映射为 ORM 对象
        stmt = insert(Photo).values(photo_dicts).returning(Photo)

        # 执行语句并获取标量结果
        result = await db.scalars(stmt)
        await db.commit()

        return list(result.all())

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
                PhotoStoryM2M.__table__, Photo.id == PhotoStoryM2M.__table__.c.photo_id
            )
            .where(PhotoStoryM2M.__table__.c.story_id == story_id)
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
    async def get_keys_for_deletion(
        cls, db: AsyncSession, photo_ids: list[UUID], user_id: UUID
    ) -> list[tuple[str, bool]]:
        """
        在删除前，极速查出所有需要去 OSS 删除的文件 Key。
        严格绑定 user_id 越权校验，防止别人猜到 UUID 删除他人的图。
        返回 (object_key, has_video) 元组列表，衍生路径由调用方推导。
        """
        stmt = select(Photo.object_key, Photo.has_video).where(
            Photo.id.in_(photo_ids), Photo.user_id == user_id
        )
        result = await db.execute(stmt)
        return list(result.all())

    @classmethod
    async def delete_many(
        cls, db: AsyncSession, photo_ids: list[UUID], user_id: UUID
    ) -> int:
        """
        原生 Core 高性能批量删除。
        返回实际删除的行数。
        """
        stmt = delete(Photo).where(Photo.id.in_(photo_ids), Photo.user_id == user_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @classmethod
    async def update_after_processing(
        cls, db: AsyncSession, photo_id: UUID, data: PhotoWorkerUpdate
    ) -> Photo | None:
        """
        Worker 专用：一次性回写所有处理结果，短事务。

        调用方应在所有 CPU 密集型计算（EXIF 解析、缩略图生成）完成后
        才调用此方法，确保 DB Session 持有时间极短。
        """
        photo = await cls.get_by_id(db, photo_id)
        if photo is None:
            return None

        #TODO：defencive programming
        photo.exif_data = data.exif_data
        photo.taken_at = data.taken_at
        photo.width = data.width
        photo.height = data.height
        photo.has_video = data.has_video
        if data.location_wkt:
            photo.location_wkt = WKTElement(data.location_wkt, srid=4326)  # type: ignore[assignment]

        await db.commit()
        await db.refresh(photo)
        return photo

    @classmethod
    async def get_orphan_photos(
        cls, db: AsyncSession, user_id: UUID, limit: int = 50
    ) -> list[Photo]:
        """获取未关联故事的照片（孤儿照片）- 通过 M2M 表反查"""
        # 子查询：所有已关联故事的照片 ID
        # 这行代码的含义是：构造一个 SQL 子查询对象，用于查找在中间表（PhotoStoryM2M）中所有已有关联的 photo_id。
        # PhotoStoryM2M.__table__.c.photo_id 表示取出 M2M 表里的 photo_id 列。
        # select(...) 构造一个只查询该字段的 SELECT 语句，然后 .subquery() 表示将这个 SQL 构造为子查询对象，
        # 这样后续主查询时可以用 `not_in(subquery)` 表示“不在这些已有关联故事的照片ID中”，用于查找“孤儿照片”。
        subquery = select(PhotoStoryM2M.__table__.c.photo_id).subquery()

        result = await db.execute(
            select(Photo)
            .where(Photo.user_id == user_id, Photo.id.not_in(subquery))
            .order_by(Photo.taken_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
