"""P10 SQLite durable dispatch: crash-safe claims and conservative recovery."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from aios_kernel.domain.task import Task
from aios_kernel.runtime.durable_dispatch import DurableDispatchStore
from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig
from aios_kernel.workers.base import _StubAdapterBase
from aios_kernel.workers.registry import WorkerRegistry


def _task(action="preflight"):
    return Task(
        goal_id="p10", title="durable isolated task",
        worker="cloudtech-v4-adapter",
        input_payload={
            "tenant_id": "tenant-a",
            "path_id": "WP-BLOGGER-RESEARCH",
            "action": action,
        },
    )


def test_committed_envelope_and_tenant_isolation_survive_store_recreation(tmp_path):
    path = tmp_path / "dispatch.sqlite3"
    one = DurableDispatchStore(path)
    task = _task()
    assert one.enqueue("run-1", task, "P0")
    assert not one.enqueue("run-1", task, "P0")
    fresh = DurableDispatchStore(path)
    assert fresh.status("run-1") == "queued"
    assert fresh.get("run-1", tenant_id="other") is None
    assert fresh.get("run-1", tenant_id="tenant-a")["priority"] == "P0"


def test_two_competing_connections_only_one_claims_same_run(tmp_path):
    store_a = DurableDispatchStore(tmp_path / "shared.sqlite3")
    store_b = DurableDispatchStore(tmp_path / "shared.sqlite3")
    assert store_a.enqueue("shared", _task(), "P2")
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(store_a.claim, "a")
        b = pool.submit(store_b.claim, "b")
        claims = [a.result(), b.result()]
    winners = [claim for claim in claims if claim]
    assert len(winners) == 1
    winner = winners[0]
    assert winner["fence"] == 1
    old_owner = "other"
    assert not store_a.finish("shared", old_owner, 1, status="completed")
    assert not store_a.finish("shared", winner["owner"], 0, status="completed")
    assert store_a.finish(
        "shared", winner["owner"], 1,
        status="completed", artifact={"real": True},
    )
    assert store_b.status("shared") == "completed"
    assert store_b.get("shared", tenant_id="tenant-a")["artifact"] == {"real": True}


def test_expired_read_only_preflight_replays_but_nonreadonly_quarantines(tmp_path):
    store = DurableDispatchStore(tmp_path / "interrupt.sqlite3")
    assert store.enqueue("safe", _task("preflight"), "P0")
    assert store.enqueue("unknown", _task("create_and_execute_local"), "P1")
    first = store.claim("owner", ttl_s=300)
    second = store.claim("owner2", ttl_s=300)
    assert first["run_id"] == "safe"
    assert second["run_id"] == "unknown"
    results = store.recover_expired(now=10**12)
    assert results == {"requeued_readonly": 1, "blocked_uncertain": 1}
    assert store.status("safe") == "queued"
    assert store.status("unknown") == "blocked_uncertain"
    replay = store.claim("new-owner", ttl_s=300)
    assert replay["run_id"] == "safe"
    assert replay["fence"] == 2
    assert not store.finish(
        "safe", first["owner"], first["fence"], status="completed",
    )
    assert store.claim("second-new-owner") is None


@pytest.mark.asyncio
async def test_real_scheduler_writes_and_recovers_artifact_after_restart(tmp_path):
    dbpath = tmp_path / "scheduler.sqlite3"
    registry = WorkerRegistry()
    registry.register(_StubAdapterBase("codex-adapter"))
    cfg = SchedulerConfig(max_concurrent=1, max_retries=0)
    first = AIOSScheduler(
        registry=registry, config=cfg, durable_db_path=str(dbpath)
    )
    await first.start()
    try:
        rid = await first.submit(Task(goal_id="p10", title="demo"), priority=__import__(
            "aios_kernel.scheduler", fromlist=["Priority"]
        ).Priority.P0)
        for _ in range(200):
            if (await first.status(rid))["state"] == "completed":
                break
            await asyncio.sleep(.01)
        assert (await first.status(rid))["state"] == "completed"
    finally:
        await first.stop()

    after_restart = AIOSScheduler(
        registry=registry, config=cfg, durable_db_path=str(dbpath),
    )
    # No scheduler.start() required for historical status/artifact retrieval.
    assert (await after_restart.status(rid))["state"] == "completed"
    restored = await after_restart.result(rid)
    assert restored["available"] is True
    assert restored["artifact"]["inline_json"]["worker"] == "codex-adapter"
    assert restored["business_validated"] is False


@pytest.mark.asyncio
async def test_scheduler_submission_is_durable_before_dispatch(tmp_path):
    dbpath = tmp_path / "not-started.sqlite3"
    registry = WorkerRegistry()
    registry.register(_StubAdapterBase("codex-adapter"))
    # enqueue before .start(): process could exit immediately after submit.
    first = AIOSScheduler(registry=registry, durable_db_path=str(dbpath))
    rid = await first.submit(Task(goal_id="p10", title="not yet started"))
    assert DurableDispatchStore(dbpath).status(rid) == "queued"

    restarted = AIOSScheduler(
        registry=registry, durable_db_path=str(dbpath),
        config=SchedulerConfig(max_concurrent=1),
    )
    await restarted.start()
    try:
        for _ in range(200):
            if (await restarted.status(rid))["state"] == "completed":
                break
            await asyncio.sleep(.01)
        assert (await restarted.status(rid))["state"] == "completed"
    finally:
        await restarted.stop()



class _TimedOutWorker(_StubAdapterBase):
    async def execute(self, task):
        # A failed response is NOT proof the remote side effect did not occur.
        raise TimeoutError("remote response was lost")


@pytest.mark.asyncio
async def test_failed_nonreadonly_worker_quarantined_without_auto_retry(tmp_path):
    registry = WorkerRegistry()
    registry.register(_TimedOutWorker("cloudtech-v4-adapter"))
    dbpath = tmp_path / "no-blind-retry.db"
    scheduler = AIOSScheduler(
        registry=registry,
        config=SchedulerConfig(max_concurrent=1, max_retries=3),
        durable_db_path=str(dbpath),
    )
    await scheduler.start()
    try:
        rid = await scheduler.submit(_task("create_and_execute_local"))
        for _ in range(150):
            state = (await scheduler.status(rid))["state"]
            if state == "blocked_uncertain":
                break
            await asyncio.sleep(.01)
        assert (await scheduler.status(rid))["state"] == "blocked_uncertain"
        # A dangerous failed operation must not re-enter queue automatically.
        assert DurableDispatchStore(dbpath).claim("other-worker") is None
    finally:
        await scheduler.stop()
