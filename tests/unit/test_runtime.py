"""test_runtime.py - Tests for runtime/process + memory + cron (R1503-010/011/012)."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path

import pytest

from aios_kernel.runtime.cron import CronManager, matches
from aios_kernel.runtime.memory import MemoryPersistence
from aios_kernel.runtime.process import ProcessManager, ProcessStatus

# ----- process.py ----------------------------------------------------------


@pytest.mark.asyncio
async def test_process_manager_lifecycle():
    pm = ProcessManager()
    rec = await pm.start(
        "echo-test",
        ["python", "-c", "import time; time.sleep(0.5)"],
    )
    assert rec.status == ProcessStatus.RUNNING
    assert rec.pid > 0
    assert rec.name == "echo-test"
    rec2 = await pm.stop("echo-test")
    assert rec2.status in (ProcessStatus.STOPPED, ProcessStatus.FAILED)
    # wait for completion
    await asyncio.wait_for(pm.wait("echo-test"), timeout=5.0)


@pytest.mark.asyncio
async def test_process_manager_list():
    pm = ProcessManager()
    assert pm.list() == []
    await pm.start("x", ["python", "-c", "import time; time.sleep(0.5)"])
    await pm.start("y", ["python", "-c", "import time; time.sleep(0.5)"])
    assert {r.name for r in pm.list()} == {"x", "y"}
    await pm.stop("x")
    await pm.stop("y")


@pytest.mark.asyncio
async def test_process_manager_double_start_raises():
    pm = ProcessManager()
    await pm.start("p", ["python", "-c", "import time; time.sleep(0.5)"])
    with pytest.raises(RuntimeError):
        await pm.start("p", ["python", "-c", "import time; time.sleep(0.5)"])
    await pm.stop("p")


# ----- memory.py -----------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_persistence_append_and_read(tmp_path: Path):
    mp = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    mp.append_ledger({"type": "task_submitted", "task_id": "t1"})
    mp.append_ledger({"type": "task_completed", "task_id": "t1"})
    events = mp.read_ledger()
    assert len(events) == 2
    assert events[0]["type"] == "task_submitted"
    assert events[1]["type"] == "task_completed"
    assert events[0]["task_id"] == "t1"


@pytest.mark.asyncio
async def test_memory_persistence_read_since_ts(tmp_path: Path):
    mp = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    mp.append_ledger({"type": "e1"})
    time.sleep(0.05)
    ts_cut = time.time()
    time.sleep(0.05)
    mp.append_ledger({"type": "e2"})
    events = mp.read_ledger(since_ts=ts_cut)
    assert len(events) == 1
    assert events[0]["type"] == "e2"


@pytest.mark.asyncio
async def test_memory_state_get_set_delete(tmp_path: Path):
    mp = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    assert mp.state_get("k") is None
    mp.state_set("k", "v")
    assert mp.state_get("k") == "v"
    assert mp.state_keys() == ["k"]
    # new instance reads back from disk
    mp2 = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    assert mp2.state_get("k") == "v"
    assert mp2.state_delete("k") is True
    assert mp2.state_get("k") is None


@pytest.mark.asyncio
async def test_memory_snapshot_restore(tmp_path: Path):
    mp = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    mp.state_set("a", "1")
    mp.state_set("b", "2")
    snap = mp.snapshot()
    mp.state_delete("a")
    assert mp.state_get("a") is None
    mp.restore(snap)
    assert mp.state_get("a") == "1"
    assert mp.state_get("b") == "2"


# ----- cron.py -------------------------------------------------------------


def test_cron_matches_simple():
    # every minute
    assert matches("* * * * *", datetime(2026, 10, 12, 13, 0))


def test_cron_matches_specific_minute():
    # at 13:30
    assert matches("30 13 * * *", datetime(2026, 10, 12, 13, 30))
    assert not matches("30 13 * * *", datetime(2026, 10, 12, 13, 31))


def test_cron_matches_every_5_minutes():
    expr = "*/5 * * * *"
    assert matches(expr, datetime(2026, 10, 12, 13, 0))
    assert matches(expr, datetime(2026, 10, 12, 13, 5))
    assert not matches(expr, datetime(2026, 10, 12, 13, 3))


def test_cron_matches_weekday():
    # weekdays only (1-5 in cron = Mon-Fri; weekday() in py returns 0=Mon)
    expr = "0 9 * * 1-5"
    monday = datetime(2026, 10, 12, 9, 0)  # 2026-10-12 = Mon
    sunday = datetime(2026, 10, 11, 9, 0)   # 2026-10-11 = Sun
    assert monday.weekday() == 0
    assert matches(expr, monday)
    assert not matches(expr, sunday)


def test_cron_matches_invalid_expr_raises():
    with pytest.raises(ValueError):
        matches("* * *", datetime(2026, 10, 12, 13, 0))


def test_cron_manager_register_and_list():
    cm = CronManager()
    assert cm.list() == []

    async def noop():
        return None

    cm.register("a", "* * * * *", noop)
    cm.register("b", "0 * * * *", noop)
    assert {j.name for j in cm.list()} == {"a", "b"}


def test_cron_manager_unregister():
    cm = CronManager()

    async def noop():
        return None

    cm.register("a", "* * * * *", noop)
    cm.unregister("a")
    assert cm.list() == []


def test_cron_manager_register_duplicate_raises():
    cm = CronManager()

    async def noop():
        return None

    cm.register("a", "* * * * *", noop)
    with pytest.raises(ValueError):
        cm.register("a", "* * * * *", noop)


@pytest.mark.asyncio
async def test_cron_manager_start_stop():
    cm = CronManager()

    async def noop():
        return None

    cm.register("a", "* * * * *", noop)
    await cm.start()
    # let one tick pass
    await asyncio.sleep(0.1)
    await cm.stop()
