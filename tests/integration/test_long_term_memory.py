"""test_long_term_memory.py — B003 Long-term Memory integration test."""
from __future__ import annotations
import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_put_and_get_roundtrip():
    from aios_kernel.context.long_term_memory import LongTermMemoryService, MIN_RETENTION_DAYS
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = LongTermMemoryService(factory)
            await svc.put(key="k1", value={"v": "x"}, retention_days=60, tags=["test"])
            v = await svc.get("k1")
            assert v["v"] == "x"
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_retention_days_below_30_rejected():
    from aios_kernel.context.long_term_memory import LongTermMemoryService, RetentionPolicyError
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = LongTermMemoryService(factory)
            with pytest.raises(RetentionPolicyError):
                await svc.put(key="k", value={"v": 1}, retention_days=10)
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_query_by_tag():
    from aios_kernel.context.long_term_memory import LongTermMemoryService
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = LongTermMemoryService(factory)
            await svc.put(key="a", value={"a": 1}, retention_days=30, tags=["alpha"])
            await svc.put(key="b", value={"b": 2}, retention_days=30, tags=["beta"])
            await svc.put(key="c", value={"c": 3}, retention_days=30, tags=["alpha", "common"])
            results = await svc.query(tags=["alpha"])
            assert len(results) == 2
            keys = sorted(r.key for r in results)
            assert keys == ["a", "c"]
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_source_evidence_backlink():
    from aios_kernel.context.long_term_memory import LongTermMemoryService
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = LongTermMemoryService(factory)
            ev_id = uuid4()
            await svc.put(key="k", value={"v": 1}, retention_days=30, source_evidence_id=ev_id)
            v = await svc.get("k")
            assert v.get("source_evidence_id") == str(ev_id) or v.get("source_evidence_id") == ev_id
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_delete_explicit_only():
    from aios_kernel.context.long_term_memory import LongTermMemoryService
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import SqlAlchemyRepository
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            svc = LongTermMemoryService(factory)
            await svc.put(key="k", value={"v": 1}, retention_days=30)
            assert await svc.get("k") is not None
            await svc.delete("k")
            assert await svc.get("k") is None
    finally:
        await drop_all(eng)
        await eng.dispose()
