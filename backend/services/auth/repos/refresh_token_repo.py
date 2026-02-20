from datetime import UTC, datetime
from uuid import UUID

import uuid6
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.models.refresh_token_model import RefreshToken
from services.auth.utils.token_util import TokenUtil


class RefreshTokenRepo:
    """RefreshToken 表的 CRUD 操作仓库"""

    @classmethod
    async def upsert_refresh_token(
        cls,
        db: AsyncSession,
        user_id: UUID,
        device_id: UUID,
        refresh_token: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """
        创建或更新 refresh_token（UPSERT）+ 更新用户最后活跃时间
        - 使用 device_id 作为冲突检测锚点
        - 同一设备重复登录：更新该设备的 token
        - 不同设备登录：创建新的 token 记录
        - 同时更新用户的 last_active_at
        使用 PostgreSQL CTE (WITH) 在一条 SQL 中完成两个写操作
        """
        token_hash = TokenUtil.make_hash_token(refresh_token)
        new_token_id = uuid6.uuid7()
        # 使用 CTE：UPSERT token + 更新用户 last_active_at
        sql = text("""
        WITH token_upsert AS (
            INSERT INTO auth.refresh_token (id, user_id, device_id, token_hash, expires_at)
            VALUES (:id, :user_id, :device_id, :token_hash, :expires_at)
            ON CONFLICT (user_id, device_id)
            DO UPDATE SET
                token_hash = EXCLUDED.token_hash,
                expires_at = EXCLUDED.expires_at
            RETURNING id, user_id
        ),
        user_update AS (
            UPDATE auth.user
            SET last_active_at = NOW()
            FROM token_upsert
            WHERE auth.user.id = token_upsert.user_id
        )
        SELECT id FROM token_upsert;
    """)

        result = await db.execute(
            sql,
            {
                "id": new_token_id,
                "user_id": user_id,
                "device_id": device_id,
                "token_hash": token_hash,
                "expires_at": expires_at,
            },
        )
        await db.commit()

        # 获取返回的 token id
        token_id = result.scalar_one()

        # 查询刚创建/更新的 token 返回
        new_token = await db.get(RefreshToken, token_id)
        return new_token

    @classmethod
    async def get_refresh_token(
        cls, db: AsyncSession, refresh_token: str
    ) -> RefreshToken | None:
        """
        查询 refresh_token
        """
        token_hash = TokenUtil.make_hash_token(refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_user_refresh_token(
        cls, db: AsyncSession, user_id: UUID
    ) -> RefreshToken | None:
        """
        获取用户的 refresh_token（一个用户只有一个）
        """
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def delete_refresh_token(cls, db: AsyncSession, token: RefreshToken) -> None:
        """
        删除 refresh_token
        """
        await db.delete(token)
        await db.commit()

    @classmethod
    async def delete_refresh_token_by_user_id(
        cls, db: AsyncSession, user_id: UUID
    ) -> None:
        """
        删除用户的 refresh_token（使用原生 SQL）
        """
        sql = text("DELETE FROM auth.refresh_token WHERE user_id = :user_id")
        await db.execute(sql, {"user_id": user_id})
        await db.commit()

    @classmethod
    async def clean_expired_tokens(cls, db: AsyncSession) -> int:
        """
        清理所有过期的 refresh_token（定时任务使用）
        使用原生 SQL 批量删除
        """
        now = datetime.now(UTC)

        # 先查询数量
        count_sql = text(
            "SELECT COUNT(*) FROM auth.refresh_token WHERE expires_at <= :now"
        )
        result = await db.execute(count_sql, {"now": now})
        count = result.scalar()

        # 批量删除
        if count > 0:
            delete_sql = text("DELETE FROM auth.refresh_token WHERE expires_at <= :now")
            await db.execute(delete_sql, {"now": now})
            await db.commit()

        return count
