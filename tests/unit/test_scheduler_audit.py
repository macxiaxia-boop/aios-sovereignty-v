"""test_scheduler_audit.py - Scheduler audit ledger integration (R1503-FINAL gap-fill)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from aios_kernel.domain.task import Task, TaskType
from aios_kernel.runtime.memory import MemoryPersistence
from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig
from aios_kernel.workers.base import HealthReport, HealthStatus, WorkerAdapter
from aios_kernel.workers.registry import WorkerRegistry


class _Stub(WorkerAdapter):
    def __init__(self, worker_id):
        self.worker_id = worker_id

    async def execute(self, task):
        from aios_kernel.domain.artifact import Artifact, ArtifactType
        return Artifact(task_id=task.id, artifact_type=ArtifactType.CUSTOM,
                       label="ok", inline_json={"w": self.worker_id})

    async def cancel(self, task_id): return None

    async def health(self):
        import datetime
        return HealthReport(worker_id=self.worker_id, status=HealthStatus.HEALTHY,
                          last_check_at=datetime.datetime.now(datetime.UTC))

    async def warmup(self): return None
    async def shutdown(self): return None


def _make(tmp_path: Path):
    reg = WorkerRegistry()
    reg.register(_Stub("w1"))
    mp = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    s = AIOSScheduler(
        registry=reg,
        config=SchedulerConfig(max_concurrent=1, max_retries=1, base_retry_delay_s=0.001),
        memory=mp,
    )
    return s, mp


@pytest.mark.asyncio
async def test_audit_records_task_submitted(tmp_path: Path):
    s, mp = _make(tmp_path)
    task = Task(goal_id="g", title="t", task_type=TaskType.CUSTOM)
    await s.submit(task)
    events = mp.read_ledger()
    assert any(e["type"] == "task_submitted" for e in events)


@pytest.mark.asyncio
async def test_audit_records_task_completed(tmp_path: Path):
    s, mp = _make(tmp_path)
    await s.start()
    try:
        task = Task(goal_id="g", title="t", task_type=TaskType.CUSTOM)
        rid = await s.submit(task)
        # wait for completion
        for _ in range(100):
            if mp.read_ledger() and any(e.get("type") == "task_completed" for e in mp.read_ledger()):
                break
            await asyncio.sleep(0.05)
        events = mp.read_ledger()
        types = {e["type"] for e in events}
        assert "task_submitted" in types
        assert "task_completed" in types
    finally:
        await s.stop()


@pytest.mark.asyncio
async def test_audit_records_dlq_on_failure(tmp_path: Path):
    class _Fail(WorkerAdapter):
        def __init__(self):
            self.worker_id = "fail"
        async def execute(self, task):
            raise RuntimeError("forced fail")
        async def cancel(self, t): return None
        async def health(self):
            import datetime
            return HealthReport(worker_id="fail", status=HealthStatus.HEALTHY,
                              last_check_at=datetime.datetime.now(datetime.UTC))
        async def warmup(self): return None
        async def shutdown(self): return None

    reg = WorkerRegistry()
    reg.register(_Fail())
    mp = MemoryPersistence(
        ledger_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )
    s = AIOSScheduler(
        registry=reg,
        config=SchedulerConfig(max_concurrent=1, max_retries=1, base_retry_delay_s=0.001),
        memory=mp,
    )
    await s.start()
    try:
        task = Task(goal_id="g", title="t", task_type=TaskType.CUSTOM)
        await s.submit(task)
        # wait for dlq
        for _ in range(100):
            if any(e["type"] == "task_dlq" for e in mp.read_ledger()):
                break
            await asyncio.sleep(0.05)
        events = mp.read_ledger()
        assert any(e["type"] == "task_dlq" for e in events)
    finally:
        await s.stop()


@pytest.mark.asyncio
async def test_scheduler_no_memory_does_not_crash(tmp_path: Path):
    """Scheduler must work fine without memory (memory is optional)."""
    reg = WorkerRegistry()
    reg.register(_Stub("w1"))
    s = AIOSScheduler(
        registry=reg,
        config=SchedulerConfig(max_concurrent=1),
        memory=None,  # explicit None
    )
    await s.start()
    try:
        task = Task(goal_id="g", title="t", task_type=TaskType.CUSTOM)
        rid = await s.submit(task)
        for _ in range(50):
            st = await s.status(rid)
            if st["state"] == "completed":
                break
            await asyncio.sleep(0.05)
        assert (await s.status(rid))["state"] == "completed"
    finally:
        await s.stop()