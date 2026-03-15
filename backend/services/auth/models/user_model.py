from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base, CreatedTimeMixin, IDMixin

if TYPE_CHECKING:
    from services.auth.models.refresh_token_model import RefreshToken


class User(Base, IDMixin, CreatedTimeMixin):
    __tablename__ = "user"
    __table_args__ = (
        # 1. 软删除的唯一性陷阱 (见下文解释)
        # 只有在未删除的情况下，Name，Email 和 Phone 才需要唯一
        Index(
            "ix_user_name_active",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "ix_user_email_active",
            "email",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "ix_user_phone_active",
            "phone",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        # 2. 配置参数 (必须放在元组的最后一位)
        {
            "schema": "auth",
            "comment": "用户核心表，存储账号及安全凭证",  # 强烈建议加上表注释
        },
    )

    name: Mapped[str] = mapped_column(String(50))

    # 账号 (唯一索引)
    # Optional(已改为|None)会创建nullable=True,没有Optional就是nullable=False
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    avatar_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 安全字段
    hashed_password: Mapped[str | None] = mapped_column(String)

    # --- 状态字段 ---
    is_deleted: Mapped[bool] = mapped_column(default=False)  # 软删除

    # --- 时间字段 ---
    # created_at 由 CreatedTimeMixin 提供
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- 🔗 关联关系 ---
    # 加上这就行了：一对多关联
    # lazy="select": 默认不查，用到 user.refresh_tokens 时再查数据库
    # cascade="all, delete-orphan": Python层面的级联删除，配合数据库层面的 ondelete="CASCADE"
    refresh_token: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
