from datetime import datetime
from uuid import UUID

import uuid6
from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UUID as SQL_UUID

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class IDMixin:
    """ID 主键 Mixin"""

    id: Mapped[UUID] = mapped_column(
        # as_uuid=True SQLAlchemy 会自动把这个字符串转换成 Python 的 uuid.UUID 对象。
        SQL_UUID(as_uuid=True),
        primary_key=True,
        # default: Python 层面的默认值，使用 ORM 时优先使用（生成 UUID v7，时间排序，更适合主键）
        default=uuid6.uuid7,
        # server_default: 数据库层面的默认值，使用原生 SQL 时使用（生成 UUID v4，作为备用）
        # 这样无论是 ORM 还是原生 SQL，都能自动生成 UUID
        server_default=text("gen_random_uuid()"),
    )


class CreatedTimeMixin:
    """创建时间 Mixin"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )


class UpdatedTimeMixin:
    """更新时间 Mixin"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


class Base(DeclarativeBase):
    """基础模型类（包含 ID）"""

    __abstract__ = True

    metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)
