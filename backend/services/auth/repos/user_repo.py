from datetime import UTC, datetime
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionDep
from core.security import get_password_hash
from services.auth.models.user_model import User


class UserRepo:
    """User 表的 CRUD 操作仓库"""

    @classmethod
    async def get_user_by_id(cls, db: AsyncSession, user_id: UUID) -> User | None:
        """
        根据用户 ID 获取用户（主键查询）
        """
        # 主键查取的专用快捷方式，返回User对象
        user = await db.get(User, user_id)
        return user

    @classmethod
    async def get_user_by_email(cls, db: AsyncSession, email: str) -> User | None:
        """
        根据邮箱获取用户
        """
        stmt = select(User).where(User.email == email)  # statement 声明式语句
        result = await db.execute(stmt)  # 执行声明式语句
        # 获取结果(单个或None)，返回select中写的User对象
        user = result.scalar_one_or_none()
        return user

    @classmethod
    async def get_user_by_phone(cls, db: AsyncSession, phone: str) -> User | None:
        """
        根据手机号获取用户
        """
        stmt = select(User).where(User.phone == phone)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        return user

    @classmethod
    async def get_user_by_email_or_phone(
        cls, db: AsyncSession, email: str | None = None, phone: str | None = None
    ) -> User | None:
        """
        根据邮箱或手机号获取用户（用于登录校验）
        """
        conditions = []
        if email:
            conditions.append(User.email == email)
        if phone:
            conditions.append(User.phone == phone)

        if not conditions:
            return None

        stmt = select(User).where(or_(*conditions))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        return user

    @classmethod
    async def create_user(
        cls,
        db: SessionDep,
        name: str,
        password: str,
        email: EmailStr | None = None,
        phone: str | None = None,
    ) -> User:
        """
        创建新用户
        - 支持邮箱注册或手机号注册
        """
        hashed_password = get_password_hash(password)
        now = datetime.now(UTC)

        user = User(
            name=name,
            email=email,
            phone=phone,
            hashed_password=hashed_password,
            last_active_at=now,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @classmethod
    async def update_avatar_key(
        cls, db: AsyncSession, user: User, avatar_key: str
    ) -> None:
        """更新用户头像存储路径"""
        user.avatar_key = avatar_key
        await db.commit()

    @classmethod
    async def soft_delete_user(cls, db: AsyncSession, user: User) -> None:
        """
        软删除用户（标记为已删除）
        """
        user.is_deleted = True
        await db.commit()

    @classmethod
    async def get_user_by_id_raw(cls, db: AsyncSession, user_id: UUID) -> User | None:
        """
        根据用户ID获取用户(原始SQL)
        """
        stmt = text("SELECT * FROM auth.user WHERE id = :user_id")
        result = await db.execute(stmt, {"user_id": user_id})
        user = result.mappings().one_or_none()
        if user is None:
            return None
        return User(**user)
