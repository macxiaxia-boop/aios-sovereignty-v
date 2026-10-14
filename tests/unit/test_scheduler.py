"""test_scheduler.py - Unit tests for AIOSScheduler (R1503-001).

Covers:
  - Priority queue ordering
  - Circuit breaker state machine
  - Metrics counters
  - Retry with backoff
  - DLQ on exhaustion
"""
from __future__ import annotations

import asyncio
import time
import uuid

import pytest

from aios_kernel.domain.artifact import Artifact, ArtifactType
from aios_kernel.domain.task import Task, TaskType
from aios_kernel.scheduler import (
    AIOSScheduler,
    CircuitBreaker,
    CircuitState,
    Priority,
    SchedulerConfig,
)
from aios_kernel.workers.base import HealthReport, HealthStatus, WorkerAdapter
from aios_kernel.workers.registry import WorkerRegistry

# ----- Fake adapters --------------------------------------------------------


class _FakeAdapter(WorkerAdapter):
    def __init__(
        self,
        worker_id: str,
        *,
        fail_n: int = 0,
        success: bool = True,
        delay_s: float = 0.0,
    ) -> None:
        self.worker_id = worker_id
        self._fail_n = fail_n
        self._calls = 0
        self._success = success
        self._delay_s = delay_s

    async def execute(self, task):
        self._calls += 1
        if self._delay_s:
            await asyncio.sleep(self._delay_s)
        if self._calls <= self._fail_n:
            raise RuntimeError(f"fake failure #{self._calls}")
        return Artifact(
            task_id=task.id,
            artifact_type=ArtifactType.CUSTOM,
            label="fake",
            inline_json={"worker": self.worker_id, "call": self._calls},
        )

    async def cancel(self, task_id):
        return None

    async def health(self):
        return HealthReport(
            worker_id=self.worker_id,
            status=HealthStatus.HEALTHY,
            last_check_at=__import__("datetime").datetime.now(
                __import__("datetime").UTC
            ),
        )

    async def warmup(self):
        return None

    async def shutdown(self):
        return None


def _make_task(idx: int = 1, worker: str | None = None) -> Task:
    """Construct a Task; uses UUID for the id (Pydantic validator requires it)."""
    return Task(
        id=str(uuid.uuid4()),
        goal_id="g-1",
        title=f"task {idx}",
        task_type=TaskType.CUSTOM,
        worker=worker,
    )


def _make_registry(*adapters: WorkerAdapter) -> WorkerRegistry:
    r = WorkerRegistry()
    for a in adapters:
        r.register(a)
    return r


# ----- Tests ----------------------------------------------------------------


def test_circuit_breaker_initial_state_is_closed():
    cb = CircuitBreaker()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow() is True


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.allow()
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert not cb.allow()


def test_circuit_breaker_recovery_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=0.01)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert not cb.allow()
    time.sleep(0.02)
    assert cb.allow()  # HALF_OPEN probe


def test_half_open_admits_only_one_inflight_probe():
    """Do not fan out a recovered worker into many concurrent AI tasks."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=0.01)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    cb.opened_at = time.time() - 1  # deterministic elapsed timeout
    assert cb.allow() is True   # exactly one recovery probe
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.allow() is False  # overlapping worker request must be rejected
    assert cb.allow() is False
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow() is True   # recovered worker can resume normal traffic


def test_half_open_failed_probe_opens_and_requires_new_timeout():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout_s=30)
    for _ in range(3):
        cb.record_failure()
    cb.opened_at = time.time() - 31
    assert cb.allow()
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow() is False


def test_circuit_breaker_closes_on_half_open_success():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=0.01)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.02)
    cb.allow()  # → HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_scheduler_submit_returns_run_id():
    registry = _make_registry(_FakeAdapter("w1"))
    scheduler = AIOSScheduler(registry=registry)
    task = _make_task(1)
    run_id = await scheduler.submit(task, priority=Priority.P1)
    assert run_id.startswith("run-")
    assert task.id in run_id


@pytest.mark.asyncio
async def test_scheduler_dispatches_and_completes():
    fake = _FakeAdapter("w1")
    registry = _make_registry(fake)
    scheduler = AIOSScheduler(registry=registry, config=SchedulerConfig(max_concurrent=1))
    await scheduler.start()
    try:
        task = _make_task(1)
        await scheduler.submit(task, priority=Priority.P1)
        # wait for completion via metrics (active drains before status reflects it)
        for _ in range(100):
            snap = scheduler.metrics()
            if snap["completed"] >= 1:
                break
            await asyncio.sleep(0.05)
        assert fake._calls == 1
        snap = scheduler.metrics()
        assert snap["submitted"] == 1
        assert snap["completed"] == 1
        assert snap["failed"] == 0
        assert snap["avg_dispatch_latency_s"] >= 0
    finally:
        await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_retries_then_dlq():
    fake = _FakeAdapter("w1", fail_n=10)  # always fail
    registry = _make_registry(fake)
    # Use a circuit-breaker whose threshold matches our retry budget (3 attempts
    # = 1 initial + 2 retries) so we can assert OPEN within this test.
    scheduler = AIOSScheduler(
        registry=registry,
        config=SchedulerConfig(max_concurrent=1, max_retries=2, base_retry_delay_s=0.001),
    )
    # Force the breaker threshold to 3 (matches retry attempts) by replacing
    # the auto-created one after construction.
    scheduler._breakers["w1"] = CircuitBreaker(failure_threshold=3)
    await scheduler.start()
    try:
        await scheduler.submit(_make_task(1), priority=Priority.P2)
        # wait for the retry chain to fully terminate: 1 initial + 2 retries -> DLQ.
        for _ in range(200):
            snap = scheduler.metrics()
            if snap["dlq_size"] >= 1 and snap["failed"] >= 1:
                break
            await asyncio.sleep(0.05)
        snap = scheduler.metrics()
        assert snap["submitted"] == 1
        assert snap["failed"] == 1
        assert snap["retried"] >= 1
        assert snap["dlq_size"] == 1
        # circuit should be OPEN (3 = fail_threshold)
        assert scheduler._breakers["w1"].state == CircuitState.OPEN
    finally:
        await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_priority_ordering():
    fake = _FakeAdapter("w1", delay_s=0.05)
    registry = _make_registry(fake)
    scheduler = AIOSScheduler(registry=registry, config=SchedulerConfig(max_concurrent=1))
    await scheduler.start()
    try:
        # submit P2 first, then P0
        await scheduler.submit(_make_task(2), priority=Priority.P2)
        await asyncio.sleep(0.01)  # let P2 start
        await scheduler.submit(_make_task(0), priority=Priority.P0)
        # P0 should be queued
        snap = scheduler.metrics()
        assert snap["queue_depth_by_priority"]["P0"] >= 1
    finally:
        await scheduler.stop()


def test_priority_enum_default():
    """Unspecified priority defaults to P2."""
    assert Priority("not-a-priority") == Priority.P2  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_scheduler_metrics_snapshot_fields():
    fake = _FakeAdapter("w1")
    registry = _make_registry(fake)
    scheduler = AIOSScheduler(registry=registry)
    snap = scheduler.metrics()
    for key in (
        "submitted", "completed", "failed", "retried",
        "dlq_size", "queue_depth_by_priority",
        "avg_dispatch_latency_s", "circuit_opened",
    ):
        assert key in snap
