import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base_model import Base, CreatedTimeMixin, IDMixin

if TYPE_CHECKING:
    from services.auth.models.user_model import User


class RefreshToken(Base, IDMixin, CreatedTimeMixin):
    __tablename__ = "refresh_token"
    __table_args__ = (
        # 核心逻辑: 一个用户 + 一个设备 = 唯一的一个 Token 记录
        # 这就是 UPSERT (Insert on Conflict Update) 的依据
        UniqueConstraint("user_id", "device_id", name="uq_refresh_tokens_user_device"),
        # 索引优化: 经常需要查询 "这个用户的所有过期 Token" 进行清理
        Index("ix_refresh_tokens_user_expires", "user_id", "expires_at"),
        # 配置参数
        {"schema": "auth", "comment": "Refresh Token 存储表，支持多端登录"},
    )

    # 关联用户 (级联删除：用户注销，Token 自动清理)
    # unique=True: 一个用户只能有一个 refresh_token，用于 UPSERT 冲突检测
    # ondelete="CASCADE" (级联删除) -- 用户注销，Token 自动清理
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.user.id", ondelete="CASCADE"), index=True
    )

    # 🔐 核心安全字段
    # 我们只存 refresh_token 的哈希值。
    # 即使黑客拖库，拿到的也是一堆乱码，无法伪造身份。
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)

    # ⏳ 生命周期
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # created_at 由 CreatedTimeMixin 提供

    device_id: Mapped[uuid.UUID] = mapped_column(unique=True)

    # 反向关联 (方便通过 user.refresh_tokens 查询)
    # 字符串引用 "User" 避免循环导入
    user: Mapped["User"] = relationship(back_populates="refresh_token")

    def __repr__(self):
        """
        "Representation"（表现形式）
        没有它时: 如果你直接打印一个对象 print(token_obj)，
        Python 默认会输出类似 <RefreshToken object at 0x7f8b1c2d3e> 的内存地址。
        这对开发者调试毫无意义，因为你看不出这个对象里存了什么数据。
        """
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
