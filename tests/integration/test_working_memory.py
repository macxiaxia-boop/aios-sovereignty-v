"""test_working_memory.py — B002 Working Memory integration test."""
from __future__ import annotations
import pytest

from aios_kernel.context.working_memory import (
    DEFAULT_TTL,
    WorkingMemoryEntry,
    WorkingMemoryService,
)


@pytest.mark.asyncio
async def test_put_and_get_roundtrip():
    from datetime import timedelta
    from aios_kernel.domain.services.repository import session_scope, make_session_factory
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    from aios_kernel.persistence import WorkingMemoryORM

    from aios_kernel.domain.services.repository import make_engine
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = WorkingMemoryService(factory)
            await svc.put("session-A", "current_goal", {"goal_id": "g-1"})
            v = await svc.get("session-A", "current_goal")
            assert v == {"goal_id": "g-1"}
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_session_isolation():
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = WorkingMemoryService(factory)
            await svc.put("session-A", "key1", {"v": "A"})
            await svc.put("session-B", "key1", {"v": "B"})
            assert await svc.get("session-A", "key1") == {"v": "A"}
            assert await svc.get("session-B", "key1") == {"v": "B"}
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_ttl_expires():
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    from datetime import timedelta
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = WorkingMemoryService(factory)
            await svc.put("session-X", "k", {"v": 1}, ttl=timedelta(seconds=-1))
            assert await svc.get("session-X", "k") is None
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_list_keys():
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = WorkingMemoryService(factory)
            await svc.put("session-Y", "a", {"a": 1})
            await svc.put("session-Y", "b", {"b": 2})
            await svc.put("session-Y", "c", {"c": 3})
            keys = await svc.list_keys("session-Y")
            assert set(keys) == {"a", "b", "c"}
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_clear_session():
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = WorkingMemoryService(factory)
            await svc.put("session-Z", "x", {"x": 1})
            await svc.put("session-Z", "y", {"y": 2})
            await svc.clear_session("session-Z")
            assert await svc.get("session-Z", "x") is None
            assert await svc.get("session-Z", "y") is None
    finally:
        await drop_all(eng)
        await eng.dispose()
