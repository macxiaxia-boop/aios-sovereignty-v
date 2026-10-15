"""P6: scheduler dispatch outcome tracking with optional existing MemoryPersistence.

This deliberately tests *observed worker outcomes*, not verified business
success, nor durable-queue replay or multi-process lease safety.
"""
from __future__ import annotations

import asyncio

import pytest

from aios_kernel.domain.task import Task
from aios_kernel.runtime.memory import MemoryPersistence
from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig
from aios_kernel.workers.base import _StubAdapterBase
from aios_kernel.workers.registry import WorkerRegistry


def _scheduler(*, memory=None, worker=None, max_retries=0):
    registry = WorkerRegistry()
    registry.register(worker or _StubAdapterBase("codex-adapter"))
    return AIOSScheduler(
        registry=registry,
        config=SchedulerConfig(max_concurrent=1, max_retries=max_retries),
        memory=memory,
    )


async def _until_status(scheduler, run_id, value):
    for _ in range(200):
        result = await scheduler.status(run_id)
        if result["state"] == value:
            return result
        await asyncio.sleep(0.005)
    raise AssertionError(f"status did not become {value}: {await scheduler.status(run_id)}")


@pytest.mark.asyncio
async def test_status_remains_completed_after_active_task_evicted():
    scheduler = _scheduler()
    await scheduler.start()
    try:
        run_id = await scheduler.submit(Task(goal_id="g", title="demo"))
        await _until_status(scheduler, run_id, "completed")
        # on_done callback prunes _active; status must not fall to unknown.
        await asyncio.sleep(0.02)
        assert (await scheduler.status(run_id))["state"] == "completed"
    finally:
        await scheduler.stop()


@pytest.mark.asyncio
async def test_outcome_survives_scheduler_recreation_with_memory(tmp_path):
    memory = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    scheduler = _scheduler(memory=memory)
    await scheduler.start()
    try:
        run_id = await scheduler.submit(Task(goal_id="g", title="persisted"))
        await _until_status(scheduler, run_id, "completed")
    finally:
        await scheduler.stop()

    fresh_memory = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    fresh_scheduler = _scheduler(memory=fresh_memory)
    assert (await fresh_scheduler.status(run_id))["state"] == "completed"


class _FailingWorker(_StubAdapterBase):
    async def execute(self, task):
        raise RuntimeError("injected failure")


@pytest.mark.asyncio
async def test_failed_run_persists_failure_even_after_dlq(tmp_path):
    memory = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    scheduler = _scheduler(
        memory=memory,
        worker=_FailingWorker("codex-adapter"),
        max_retries=0,
    )
    await scheduler.start()
    try:
        run_id = await scheduler.submit(Task(goal_id="g", title="fails"))
        await _until_status(scheduler, run_id, "failed")
        await asyncio.sleep(0.02)
        assert (await scheduler.status(run_id))["state"] == "failed"
    finally:
        await scheduler.stop()


@pytest.mark.asyncio
async def test_unknown_run_remains_unknown(tmp_path):
    memory = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    scheduler = _scheduler(memory=memory)
    assert (await scheduler.status("missing"))["state"] == "unknown"
