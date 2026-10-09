"""Alembic env.py - AIOS Kernel migrations.

Loads SQLAlchemy metadata from aios_kernel.persistence.models.Base,
connects to the URL in alembic.ini (or AIOS_KERNEL_DATABASE_URL), and
runs migrations in online mode (async engine for SQLite/aiosqlite).
"""
from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig

# Make sure the kernel package is importable.
HERE = os.path.dirname(os.path.abspath(__file__))
KERNEL_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(KERNEL_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import the Base so metadata is populated.
from aios_kernel.persistence.models import Base  # noqa: E402

# Alembic Config object.
config = context.config

# Override URL from env if set.
ENV_URL = os.environ.get("AIOS_KERNEL_DATABASE_URL") or os.environ.get('AIOS_KERNEL_DATABASE_URL')
if ENV_URL:
    config.set_main_option("sqlalchemy.url", ENV_URL)

# Configure loggers from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
