"""test_workers.py - 4 adapter + registry + routing tests."""
from __future__ import annotations
import pytest

from aios_kernel.workers import (
    ClaudeCodeAdapter,
    CodexAdapter,
    HealthReport,
    HealthStatus,
    HermesAdapter,
    NotRegistered,
    OpenClawAdapter,
    WorkerAdapter,
    WorkerRegistry,
)
from aios_kernel.domain.task import Task, TaskType
from aios_kernel.domain.envelope import utcnow


def test_worker_adapter_protocol():
    assert hasattr(WorkerAdapter, "execute")
    assert hasattr(WorkerAdapter, "cancel")
    assert hasattr(WorkerAdapter, "health")
    assert hasattr(WorkerAdapter, "warmup")
    assert hasattr(WorkerAdapter, "shutdown")


def test_health_status_values():
    assert HealthStatus.HEALTHY.value == "healthy"
    assert HealthStatus.DEGRADED.value == "degraded"
    assert HealthStatus.UNHEALTHY.value == "unhealthy"


def test_health_report_dataclass():
    r = HealthReport(worker_id="x", status=HealthStatus.HEALTHY, last_check_at=utcnow())
    assert r.worker_id == "x"
    assert r.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_codex_adapter():
    a = CodexAdapter()
    assert a.worker_id == "codex-adapter"
    t = Task(goal_id="g-1", title="t", task_type=TaskType.FILE_SUMMARY)
    art = await a.execute(t)
    assert art.task_id == t.id
    assert art.label == "stub"
    assert art.inline_json["worker"] == "codex-adapter"
    h = await a.health()
    assert h.status == HealthStatus.HEALTHY
    await a.cancel(t.id)
    await a.shutdown()


@pytest.mark.asyncio
async def test_claude_code_adapter():
    a = ClaudeCodeAdapter()
    assert a.worker_id == "claude-code-adapter"
    t = Task(goal_id="g-1", title="t", task_type=TaskType.MATH_CALC)
    art = await a.execute(t)
    assert art.inline_json["worker"] == "claude-code-adapter"


@pytest.mark.asyncio
async def test_openclaw_adapter():
    a = OpenClawAdapter()
    assert a.worker_id == "openclaw-adapter"
    t = Task(goal_id="g-1", title="t", task_type=TaskType.ENV_PROBE)
    art = await a.execute(t)
    assert art.inline_json["worker"] == "openclaw-adapter"


@pytest.mark.asyncio
async def test_hermes_adapter():
    a = HermesAdapter()
    assert a.worker_id == "hermes-adapter"
    t = Task(goal_id="g-1", title="t", task_type=TaskType.CROSS_WORKER)
    art = await a.execute(t)
    assert art.inline_json["worker"] == "hermes-adapter"


def test_registry_register_and_get():
    r = WorkerRegistry()
    r.register(CodexAdapter())
    r.register(ClaudeCodeAdapter())
    assert sorted(r.list_ids()) == ["claude-code-adapter", "codex-adapter"]
    assert r.get("codex-adapter").worker_id == "codex-adapter"


def test_registry_get_unknown_raises():
    r = WorkerRegistry()
    with pytest.raises(NotRegistered):
        r.get("nope")


def test_registry_route_preferred():
    r = WorkerRegistry()
    r.register(CodexAdapter())
    r.register(ClaudeCodeAdapter())
    t = Task(goal_id="g-1", title="t", task_type=TaskType.CUSTOM, worker="claude-code-adapter")
    assert r.route(t).worker_id == "claude-code-adapter"


def test_registry_route_by_type():
    r = WorkerRegistry()
    r.register(CodexAdapter())
    r.register(ClaudeCodeAdapter())
    r.register(OpenClawAdapter())
    r.register(HermesAdapter())
    t1 = Task(goal_id="g-1", title="t", task_type=TaskType.FILE_SUMMARY)
    t2 = Task(goal_id="g-1", title="t", task_type=TaskType.MATH_CALC)
    t3 = Task(goal_id="g-1", title="t", task_type=TaskType.ENV_PROBE)
    t4 = Task(goal_id="g-1", title="t", task_type=TaskType.CROSS_WORKER)
    assert r.route(t1).worker_id == "codex-adapter"
    assert r.route(t2).worker_id == "claude-code-adapter"
    assert r.route(t3).worker_id == "openclaw-adapter"
    assert r.route(t4).worker_id == "hermes-adapter"


def test_registry_route_round_robin():
    r = WorkerRegistry()
    r.register(CodexAdapter())
    t = Task(goal_id="g-1", title="t", task_type=TaskType.CUSTOM)
    first = r.route(t).worker_id
    second = r.route(t).worker_id
    assert first == "codex-adapter"
    assert second == "codex-adapter"
