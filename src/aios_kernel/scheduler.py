"""scheduler.py - AIOS High-Level Task Scheduler (R1503-001).

This module provides the AIOSScheduler class, a higher-level orchestrator that
sits on top of:
  - WorkflowEngine (durable execution adapter, T0033)
  - WorkerRegistry (4-Agent Worker Adapter routing, T0034)

Responsibilities (R1503-001 acceptance):
  1. Accept Task submission via async API
  2. Priority queue (P0 > P1 > P2)
  3. Dispatch to Worker via WorkerRegistry
  4. Retry policy with exponential backoff
  5. Circuit breaker per Worker (5 consecutive failures → OPEN)
  6. Metrics: queue_depth, completed, failed, retried, dlq_size

R1503-001: implemented by Claude Code (Agent 1 of 4-Agent team).
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aios_kernel.domain.task import Task
from aios_kernel.runtime.durable_dispatch import DurableDispatchStore
from aios_kernel.workers.base import HealthStatus
from aios_kernel.workers.registry import WorkerRegistry

log = logging.getLogger("aios_kernel.scheduler")


# ---------- Types -----------------------------------------------------------


class Priority(str, Enum):
    """Task priority levels (R1503-001 §3)."""

    P0 = "P0"  # critical, immediate
    P1 = "P1"  # high, within hour
    P2 = "P2"  # normal, default

    @classmethod
    def _missing_(cls, value):
        return cls.P2  # default to P2


class CircuitState(str, Enum):
    CLOSED = "closed"      # healthy, accept traffic
    OPEN = "open"          # failing, reject traffic (return to DLQ)
    HALF_OPEN = "half_open"  # probing


@dataclass
class CircuitBreaker:
    """Per-worker circuit breaker (R1503-001 §5)."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_ts: float = 0.0
    opened_at: float = 0.0
    failure_threshold: int = 5
    recovery_timeout_s: float = 60.0

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            log.info("circuit_breaker: HALF_OPEN → CLOSED (recovered)")
            self.state = CircuitState.CLOSED
        self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_ts = time.time()
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                log.warning("circuit_breaker: → OPEN after %d failures", self.failure_count)
                self.state = CircuitState.OPEN
                self.opened_at = time.time()

    def allow(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            # check if recovery_timeout elapsed
            if time.time() - self.opened_at >= self.recovery_timeout_s:
                log.info("circuit_breaker: OPEN → HALF_OPEN (probing)")
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # One probe was already admitted on OPEN -> HALF_OPEN. While it is
        # unresolved, reject concurrent probes; only its success or failure
        # can transition the circuit back to CLOSED or OPEN.
        return False


@dataclass
class SchedulerMetrics:
    """Scheduler observability counters (R1503-001 §6)."""

    submitted: int = 0
    completed: int = 0
    failed: int = 0
    retried: int = 0
    dlq_size: int = 0
    queue_depth_by_priority: dict = field(
        default_factory=lambda: {"P0": 0, "P1": 0, "P2": 0}
    )
    dispatch_latency_s_total: float = 0.0
    dispatch_count: int = 0
    circuit_opened: int = 0

    def snapshot(self) -> dict[str, Any]:
        avg_dispatch_latency = (
            self.dispatch_latency_s_total / self.dispatch_count
            if self.dispatch_count
            else 0.0
        )
        return {
            "submitted": self.submitted,
            "completed": self.completed,
            "failed": self.failed,
            "retried": self.retried,
            "dlq_size": self.dlq_size,
            "queue_depth_by_priority": dict(self.queue_depth_by_priority),
            "avg_dispatch_latency_s": round(avg_dispatch_latency, 4),
            "circuit_opened": self.circuit_opened,
        }


@dataclass
class SchedulerConfig:
    """Tunable parameters for AIOSScheduler."""

    max_concurrent: int = 4             # matches 4-Agent team
    max_retries: int = 3
    base_retry_delay_s: float = 1.0
    max_retry_delay_s: float = 30.0
    dlq_max_size: int = 100            # dead letter queue cap
    health_check_interval_s: float = 30.0


# ---------- Scheduler ------------------------------------------------------


class AIOSScheduler:
    """High-level task scheduler integrating WorkflowEngine + WorkerRegistry.

    Usage:
            registry = WorkerRegistry()
            registry.register(ClaudeCodeAdapter(...))
            registry.register(CodexAdapter(...))
            registry.register(OpenClawAdapter(...))
            registry.register(HermesAdapter(...))

            scheduler = AIOSScheduler(registry=registry)
            await scheduler.start()

            # submit task
            run_id = await scheduler.submit(task, priority=Priority.P1)

            # later
            status = await scheduler.status(run_id)

            await scheduler.stop()
    """

    # Forward-reference type for memory sink (avoids circular import at module load)
    if False:  # type: ignore[unreachable]
        from aios_kernel.runtime.memory import MemoryPersistence  # noqa: F401

    def __init__(
        self,
        *,
        registry: WorkerRegistry,
        config: SchedulerConfig | None = None,
        memory: MemoryPersistence | None = None,
        durable_db_path: str | None = None,
    ) -> None:
        self._registry = registry
        self._config = config or SchedulerConfig()
        # optional audit ledger (R1503-FINAL gap-fill)
        self._memory = memory
        self._durable_store = (
            DurableDispatchStore(durable_db_path) if durable_db_path else None
        )
        self._durable_owner = uuid.uuid4().hex
        # priority → asyncio queue
        self._queues: dict[Priority, asyncio.Queue] = {
            p: asyncio.Queue() for p in Priority
        }
        self._dlq: asyncio.Queue = asyncio.Queue(maxsize=self._config.dlq_max_size)
        # per-worker circuit breaker
        self._breakers: dict[str, CircuitBreaker] = defaultdict(CircuitBreaker)
        # active tasks (run_id → asyncio.Task)
        self._active: dict[str, asyncio.Task] = {}
        # Terminal outcomes are kept even after _active tasks are pruned.
        # When a MemoryPersistence sink is supplied, statuses also survive
        # process restart. This does NOT persist/recover the execution queue.
        self._run_states: dict[str, str] = {}
        self._run_results: dict[str, dict[str, Any]] = {}
        self._run_tenants: dict[str, str | None] = {}
        self._metrics = SchedulerMetrics()
        self._stopped = False
        self._dispatcher_task: asyncio.Task | None = None
        self._health_task: asyncio.Task | None = None

    def _audit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append an event to the audit ledger (R1503-FINAL gap-fill)."""
        if self._memory is None:
            return
        try:
            self._memory.append_ledger({"type": event_type, **payload})
        except Exception as exc:  # noqa: BLE001
            log.warning("audit ledger append failed: %s", exc)

    def _record_state(self, run_id: str, state: str) -> None:
        """Record observed worker-dispatch status (not business verification)."""
        self._run_states[run_id] = state
        if self._memory is not None:
            try:
                self._memory.state_set(f"scheduler-run:{run_id}", state)
            except Exception as exc:  # noqa: BLE001
                log.error("persistent scheduler state write failed: %s", exc)

    # ----- lifecycle --------------------------------------------------------

    async def start(self) -> None:
        if self._dispatcher_task is not None:
            return
        self._stopped = False
        if self._durable_store is not None:
            self._durable_store.recover_expired()
        dispatcher = (
            self._durable_dispatcher_loop()
            if self._durable_store is not None else self._dispatcher_loop()
        )
        self._dispatcher_task = asyncio.create_task(
            dispatcher, name="aios-scheduler-dispatcher"
        )
        self._health_task = asyncio.create_task(
            self._health_loop(), name="aios-scheduler-health"
        )
        log.info("scheduler.start: dispatcher + health tasks spawned")

    async def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        for run_id, task in list(self._active.items()):
            if not task.done():
                self._record_state(run_id, "interrupted")
        for task in list(self._active.values()):
            task.cancel()
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
        if self._health_task:
            self._health_task.cancel()
        for adapter in (self._registry.list_ids()):
            try:
                await self._registry.get(adapter).shutdown()
            except Exception as exc:  # noqa: BLE001
                log.warning("shutdown failed for %s: %s", adapter, exc)
        log.info("scheduler.stop: %d active tasks cancelled", len(self._active))

    # ----- public API -------------------------------------------------------

    async def submit(
        self,
        task: Task,
        *,
        priority: Priority = Priority.P2,
    ) -> str:
        """Enqueue a task for execution. Returns the run_id."""
        if self._stopped:
            raise RuntimeError("scheduler stopped")
        self._metrics.submitted += 1
        if self._durable_store is None:
            self._metrics.queue_depth_by_priority[priority.value] += 1
        # store the task descriptor alongside priority + retry count
        envelope = {
            "task": task,
            "priority": priority,
            "retries": 0,
            "ts": time.time(),
            "run_id": f"run-{task.id}-{int(time.time() * 1000)}",
        }
        tenant = getattr(task, "input_payload", {}).get("tenant_id")
        self._run_tenants[envelope["run_id"]] = (
            str(tenant) if isinstance(tenant, str) and tenant else None
        )
        if self._durable_store is not None:
            # Commit before returning a run id: the task survives restart.
            if not self._durable_store.enqueue(envelope["run_id"], task, priority.value):
                raise RuntimeError("duplicate durable scheduler run")
        else:
            await self._queues[priority].put(envelope)
        self._record_state(envelope["run_id"], "queued")
        self._audit("task_submitted", {
            "task_id": str(task.id),
            "run_id": envelope["run_id"],
            "priority": priority.value,
            "title": task.title,
        })
        log.info(
            "scheduler.submit: task_id=%s priority=%s run_id=%s queue_depth=%d",
            task.id, priority.value, envelope["run_id"],
            self._queues[priority].qsize(),
        )
        return envelope["run_id"]

    async def status(self, run_id: str) -> dict[str, Any]:
        """Read the last observed dispatch outcome; not a verifier verdict."""
        if self._durable_store is not None:
            return {"run_id": run_id, "state": self._durable_store.status(run_id)}
        active = self._active.get(run_id)
        if active is not None and not active.done():
            return {"run_id": run_id, "state": "running"}
        state = self._run_states.get(run_id)
        if state is None and self._memory is not None:
            state = self._memory.state_get(f"scheduler-run:{run_id}")
        return {"run_id": run_id, "state": state or "unknown"}

    async def result(
        self, run_id: str, *, tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Return actual worker Artifact (never business-validated by default)."""
        if self._durable_store is not None:
            row = self._durable_store.get(run_id, tenant_id=tenant_id)
            if row is None:
                return {"run_id": run_id, "state": "unknown", "available": False}
            return {
                "run_id": run_id, "state": row["state"],
                "available": row["artifact"] is not None,
                "artifact": row["artifact"],
                "business_validated": False,
                "durability": "SQLITE_DURABLE_DISPATCH_WITH_UNCERTAIN_QUARANTINE",
            }
        owner = self._run_tenants.get(run_id)
        if owner is None and self._memory is not None:
            owner = self._memory.state_get(f"scheduler-tenant:{run_id}")
        if (tenant_id is not None and owner != tenant_id) or (
            tenant_id is None and owner is not None
        ):
            # Do not leak the existence or content of another tenant's work.
            return {"run_id": run_id, "state": "unknown", "available": False}
        status = await self.status(run_id)
        artifact = self._run_results.get(run_id)
        if artifact is None and self._memory is not None:
            artifact = self._memory.state_get(f"scheduler-result:{run_id}")
        return {
            "run_id": run_id,
            "state": status["state"],
            "available": bool(artifact),
            "artifact": artifact,
            "business_validated": False,
            "durability": (
                "OPTIONAL_MEMORY_PERSISTENCE" if self._memory is not None
                else "IN_PROCESS_ONLY"
            ),
        }

    def metrics(self) -> dict[str, Any]:
        return self._metrics.snapshot()

    # ----- internal: durable opt-in dispatcher ------------------------------

    async def _durable_dispatcher_loop(self) -> None:
        """Claim committed rows; NEVER replay ambiguous effects after crash."""
        assert self._durable_store is not None
        count = 0
        while not self._stopped:
            if len(self._active) >= self._config.max_concurrent:
                await asyncio.sleep(0.05)
                continue
            # Periodic takeover: safe preflights only; all other unknown
            # results are quarantined instead of risking duplicate effects.
            if count % 100 == 0:
                self._durable_store.recover_expired()
            count += 1
            claim = self._durable_store.claim(self._durable_owner, ttl_s=300)
            if claim is None:
                await asyncio.sleep(0.05)
                continue
            run_id = claim["run_id"]
            envelope = {
                "task": claim["task"],
                "priority": Priority(claim["priority"]),
                "retries": 0,
                "run_id": run_id,
            }
            worker = asyncio.create_task(
                self._execute_durable(envelope, claim),
                name=f"durable-worker-{run_id}",
            )
            self._active[run_id] = worker
            worker.add_done_callback(
                lambda _task, rid=run_id: self._active.pop(rid, None)
            )

    async def _execute_durable(
        self, envelope: dict[str, Any], claim: dict[str, Any],
    ) -> None:
        """Lease renewal plus CAS commit of a genuine Worker Artifact."""
        assert self._durable_store is not None
        run_id = claim["run_id"]
        owner = claim["owner"]
        fence = claim["fence"]

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(60)
                if not self._durable_store.renew(
                    run_id, owner, fence, ttl_s=300,
                ):
                    raise RuntimeError("durable dispatch lease lost")

        hb = asyncio.create_task(heartbeat())
        driver = asyncio.create_task(self._execute(envelope))
        try:
            done, _pending = await asyncio.wait(
                {driver, hb}, return_when=asyncio.FIRST_COMPLETED,
            )
            if hb in done:
                driver.cancel()
                try:
                    await driver
                except asyncio.CancelledError:
                    pass
                hb.result()
                return
            await driver
            state = self._run_states.get(run_id)
            if state == "completed":
                artifact = self._run_results.get(run_id)
                self._durable_store.finish(
                    run_id, owner, fence, status="completed",
                    artifact=artifact,
                )
            elif state == "failed":
                # Failure after an outbound request might be an ambiguous
                # remote success. Only read-only preflight is retry-safe.
                safe = self._durable_store._safe_to_replay(envelope["task"])
                self._durable_store.finish(
                    run_id, owner, fence,
                    status="failed" if safe else "blocked_uncertain",
                )
            else:
                self._durable_store.finish(
                    run_id, owner, fence, status="blocked_uncertain",
                )
        except asyncio.CancelledError:
            driver.cancel()
            raise
        except Exception as exc:
            log.exception("durable dispatch failed run=%s: %s", run_id, exc)
            self._durable_store.finish(
                run_id, owner, fence, status="blocked_uncertain",
            )
        finally:
            hb.cancel()
            if not driver.done():
                driver.cancel()
            try:
                await hb
            except asyncio.CancelledError:
                pass
            try:
                await driver
            except asyncio.CancelledError:
                pass

    # ----- internal: dispatcher --------------------------------------------

    async def _dispatcher_loop(self) -> None:
        log.info("scheduler.dispatcher: loop started")
        while not self._stopped:
            # peek P0 first; P0 > P1 > P2
            envelope = None
            for prio in (Priority.P0, Priority.P1, Priority.P2):
                if not self._queues[prio].empty():
                    envelope = await self._queues[prio].get()
                    self._metrics.queue_depth_by_priority[prio.value] -= 1
                    break
            if envelope is None:
                await asyncio.sleep(0.05)
                continue
            # throttle to max_concurrent
            while len(self._active) >= self._config.max_concurrent:
                await asyncio.sleep(0.05)
            # dispatch
            run_id = envelope["run_id"]
            coro = self._execute(envelope)
            self._record_state(run_id, "running")
            self._active[run_id] = asyncio.create_task(
                coro, name=f"scheduler-run-{run_id}"
            )
            self._active[run_id].add_done_callback(
                lambda t, rid=run_id: self._active.pop(rid, None)
            )
        log.info("scheduler.dispatcher: loop stopped")

    async def _execute(self, envelope: dict[str, Any]) -> None:
        task: Task = envelope["task"]
        priority: Priority = envelope["priority"]
        retries: int = envelope["retries"]
        run_id: str = envelope["run_id"]
        start_ts = time.time()
        try:
            adapter = self._registry.route(task)
        except Exception as exc:  # noqa: BLE001
            log.error("dispatch route failed: %s", exc)
            await self._dlq_put(envelope, exc)
            return

        breaker = self._breakers[adapter.worker_id]
        if not breaker.allow():
            log.warning(
                "circuit_breaker OPEN for worker=%s, sending to DLQ", adapter.worker_id
            )
            await self._dlq_put(envelope, RuntimeError("circuit open"))
            return

        try:
            artifact = await adapter.execute(task)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "execute failed worker=%s task=%s err=%s",
                adapter.worker_id, task.id, exc,
            )
            breaker.record_failure()
            if breaker.state == CircuitState.OPEN:
                self._metrics.circuit_opened += 1
            if self._durable_store is None and retries < self._config.max_retries:
                self._metrics.retried += 1
                envelope["retries"] = retries + 1
                delay = min(
                    self._config.base_retry_delay_s * (2 ** retries),
                    self._config.max_retry_delay_s,
                )
                await asyncio.sleep(delay)
                await self._queues[priority].put(envelope)
                self._record_state(run_id, "queued")
                self._metrics.queue_depth_by_priority[priority.value] += 1
            else:
                self._metrics.failed += 1
                await self._dlq_put(envelope, exc)
            return

        # Preserve the real worker artifact; "completed" means worker return,
        # not provider receipt reconciliation or business acceptance.
        if hasattr(artifact, "model_dump"):
            artifact_doc = artifact.model_dump(mode="json")
        elif isinstance(artifact, dict):
            artifact_doc = artifact
        else:
            raise TypeError("worker must return Artifact or JSON dict")
        self._run_results[run_id] = artifact_doc
        if self._memory is not None:
            try:
                self._memory.state_set(f"scheduler-result:{run_id}", artifact_doc)
                tenant = self._run_tenants.get(run_id)
                if tenant is not None:
                    self._memory.state_set(f"scheduler-tenant:{run_id}", tenant)
            except Exception as exc:  # noqa: BLE001
                log.error("scheduler artifact persistence failed: %s", exc)
        breaker.record_success()
        self._record_state(run_id, "completed")
        self._metrics.completed += 1
        self._metrics.dispatch_latency_s_total += time.time() - start_ts
        self._metrics.dispatch_count += 1
        self._audit("task_completed", {
            "run_id": run_id,
            "task_id": str(task.id),
            "worker": adapter.worker_id,
            "latency_s": time.time() - start_ts,
        })
        log.info(
            "execute ok worker=%s task=%s artifact_id=%s latency_s=%.3f",
            adapter.worker_id, task.id, getattr(artifact, "id", "?"),
            time.time() - start_ts,
        )

    async def _dlq_put(self, envelope: dict[str, Any], exc: Exception) -> None:
        self._record_state(envelope["run_id"], "failed")
        try:
            self._dlq.put_nowait(envelope)
        except asyncio.QueueFull:
            log.error("DLQ full, dropping envelope run_id=%s", envelope["run_id"])
            return
        self._metrics.dlq_size += 1
        self._audit("task_dlq", {
            "run_id": envelope["run_id"],
            "task_id": str(envelope["task"].id),
            "error": str(exc),
            "dlq_size": self._metrics.dlq_size,
        })
        log.error(
            "scheduler.dlq: run_id=%s err=%s dlq_size=%d",
            envelope["run_id"], exc, self._metrics.dlq_size,
        )

    # ----- internal: health ------------------------------------------------

    async def _health_loop(self) -> None:
        log.info("scheduler.health: loop started")
        while not self._stopped:
            await asyncio.sleep(self._config.health_check_interval_s)
            if self._stopped:
                break
            for worker_id in self._registry.list_ids():
                try:
                    adapter = self._registry.get(worker_id)
                    report = await adapter.health()
                    if report.status == HealthStatus.UNHEALTHY:
                        breaker = self._breakers[worker_id]
                        breaker.record_failure()
                except Exception as exc:  # noqa: BLE001
                    log.warning("health check failed worker=%s err=%s", worker_id, exc)
        log.info("scheduler.health: loop stopped")


__all__ = [
    "AIOSScheduler",
    "SchedulerConfig",
    "SchedulerMetrics",
    "Priority",
    "CircuitBreaker",
    "CircuitState",
]


# CLI bridge (referenced from cli.py)
async def run_scheduler_cli(
    registry: WorkerRegistry,
    config: SchedulerConfig | None = None,
) -> None:
    """Entry point used by `aios-kernel scheduler` CLI subcommand."""
    scheduler = AIOSScheduler(registry=registry, config=config)
    await scheduler.start()
    log.info("scheduler running. Ctrl-C to stop.")
    try:
        # idle loop until cancelled
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        await scheduler.stop()
