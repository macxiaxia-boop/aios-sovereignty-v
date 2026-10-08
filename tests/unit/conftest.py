# conftest.py - pytest fixtures shared by all unit tests.
from __future__ import annotations

import asyncio
import os
import tempfile
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio

# Force a temp SQLite URL for any test that imports aios_kernel.persistence.
_test_db_dir = tempfile.mkdtemp(prefix="aios_kernel_test_")
os.environ.setdefault("AIOS_KERNEL_DATABASE_URL", f"sqlite+aiosqlite:///{_test_db_dir}/aios_kernel.db")


@pytest.fixture(scope="session")
def event_loop_policy():
    # Use the default policy (works on Windows + Linux).
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture
async def async_engine():
    from aios_kernel.domain.services.repository import make_engine
    from aios_kernel.persistence import create_all, drop_all
    engine = make_engine()
    await create_all(engine)
    try:
        yield engine
    finally:
        await drop_all(engine)
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(async_engine):
    from aios_kernel.domain.services.repository import make_session_factory
    return make_session_factory(async_engine)


@pytest_asyncio.fixture
async def db_repo(session_factory):
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.domain.services.repository import session_scope
    async with session_scope(session_factory) as session:
        yield SqlAlchemyRepository(session)


@pytest.fixture
def in_memory_repo():
    from aios_kernel.domain.services.repository import InMemoryRepository
    return InMemoryRepository()
