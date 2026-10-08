"""test_memory_integration.py — B010 Memory+Context integration smoke."""
from __future__ import annotations
import pytest


@pytest.mark.asyncio
async def test_working_memory_long_term_chain():
    """Working memory + Long-term memory chain — basic integration."""
    from aios_kernel.context.working_memory import WorkingMemoryService
    from aios_kernel.context.long_term_memory import LongTermMemoryService
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            wm = WorkingMemoryService(factory)
            ltm = LongTermMemoryService(factory)
            # Working memory - session A
            await wm.put("session-A", "task_51_evidence", {"ref": "task_1"})
            v = await wm.get("session-A", "task_51_evidence")
            assert v["ref"] == "task_1"
            # Long-term - archive
            await ltm.put(key="task_1_evidence_archive", value={"data": "x"}, retention_days=30, tags=["test"])
            v = await ltm.get("task_1_evidence_archive")
            assert v["data"] == "x"
    finally:
        await drop_all(eng)
        await eng.dispose()


@pytest.mark.asyncio
async def test_session_isolation_integration():
    """Working memory sessions isolated."""
    from aios_kernel.context.working_memory import WorkingMemoryService
    from aios_kernel.context.long_term_memory import LongTermMemoryService
    from aios_kernel.domain.services.repository import session_scope, make_session_factory, make_engine
    from aios_kernel.persistence import create_all, drop_all
    eng = make_engine()
    await create_all(eng)
    try:
        factory = make_session_factory(eng)
        async with session_scope(factory) as session:
            wm = WorkingMemoryService(factory)
            ltm = LongTermMemoryService(factory)
            await wm.put("session-X", "shared_key", {"who": "X"})
            await wm.put("session-Y", "shared_key", {"who": "Y"})
            assert (await wm.get("session-X", "shared_key"))["who"] == "X"
            assert (await wm.get("session-Y", "shared_key"))["who"] == "Y"
    finally:
        await drop_all(eng)
        await eng.dispose()
