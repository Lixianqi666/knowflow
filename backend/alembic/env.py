import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# 确保 app 包可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base
import app.models.user  # noqa
import app.models.document  # noqa
import app.models.conversation  # noqa
import app.models.permission  # noqa
import app.models.agent  # noqa
import app.models.agent_session  # noqa
import app.models.agent_trace  # noqa
import pgvector.sqlalchemy  # noqa — 注册 Vector 类型

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


def run_migrations_offline():
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
