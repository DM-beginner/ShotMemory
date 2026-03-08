import asyncio
import sys
from logging.config import fileConfig
from os.path import abspath, dirname

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# 🔥 必须导入所有模型，让 Alembic 能扫描到它们
import core.all_models  # noqa: F401
from alembic import context
from core.base_model import Base
from core.config import settings

sys.path.append(dirname(dirname(abspath(__file__))))
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
escaped_url = str(settings.DATABASE_URL).replace("%", "%%")
config.set_main_option("sqlalchemy.url", escaped_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# 🔥 架构级魔法：动态提取你代码中用到的所有 Schema
# 遍历 Base 里的所有表，提取它们的 schema 属性，塞进一个集合 (Set) 里
target_schemas = {table.schema for table in target_metadata.tables.values()}
target_schemas.add(
    None
)  # 极其关键：必须放行 None，代表 public 模式（Alembic 自己的版本表在这里）

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    """
    Alembic 自动生成的黑名单过滤器
    """
    if type_ == "table":
        # 🛡️ PostGIS 和 Tiger Geocoder 生成的系统底表黑名单
        ignored_tables = {
            "spatial_ref_sys", "topology", "layer", "county", "faces", "edges",
            "addrfeat", "bg", "cousub", "featnames", "place", "state", "tract",
            "zcta5", "addr", "county_lookup", "countysub_lookup", "direction_lookup",
            "geocode_settings", "geocode_settings_default", "loader_lookuptables",
            "loader_platform", "loader_variables", "pagc_gaz", "pagc_lex", "pagc_rules",
            "place_lookup", "secondary_unit_lookup", "state_lookup", "street_type_lookup",
            "tabblock", "tabblock20", "zip_lookup", "zip_lookup_all", "zip_lookup_base",
            "zip_state", "zip_state_loc"
        }

        # 如果是黑名单里的表，直接告诉 Alembic：“装作没看见”
        if name in ignored_tables:
            return False
            
        # 🛡️ 2. 动态白名单拦截 (彻底告别手动维护！)
        # 如果数据库里的某个表，它的 Schema 根本不在我们刚才提取的集合里，直接无视！
        if object.schema not in target_schemas:
            return False

    # 其他所有正常表，放行！
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        include_schemas=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
