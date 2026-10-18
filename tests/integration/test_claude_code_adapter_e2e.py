"""test_claude_code_adapter_e2e.py - E2E tests for ClaudeCodeAdapter (R1504).

Verifies the full integration of ClaudeCodeAdapter with the AIOS kernel:

  1. Real binary present path (success + failure + truncation)
  2. Binary missing path (stub_fallback)
  3. WorkerRegistry routing (preferred + by task_type)
  4. AIOSScheduler dispatch + audit ledger
  5. HTTP gateway submission -> scheduler -> claude-code-adapter
  6. MCP tools/call submission -> scheduler -> claude-code-adapter
  7. Circuit breaker integration (5 consecutive failures -> OPEN)
  8. Lifecycle: warmup / health / cancel / shutdown
  9. Concurrent execution
 10. 4-Agent team registration is idempotent and includes claude-code-adapter

Co-Authored-By: Claude Code (Agent 1 / claude-code-adapter) via AIOS R1504
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aios_kernel.domain.artifact import Artifact, ArtifactType
from aios_kernel.domain.task import Task, TaskType
from aios_kernel.gateway.http import create_app
from aios_kernel.gateway.mcp import MCPServer
from aios_kernel.runtime.memory import MemoryPersistence
from aios_kernel.scheduler import (
    AIOSScheduler,
    CircuitState,
    Priority,
    SchedulerConfig,
)
from aios_kernel.workers import (
    ClaudeCodeAdapter,
    CodexAdapter,
    HealthStatus,
    WorkerRegistry,
)

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


# Fake "claude" binary that understands the real ClaudeCodeAdapter arg layout:
#   fake_claude [--print] [--output-format json] [--fail N] [--big N] [--sleep MS] <message>
# Echoes the message as JSON to stdout and exits with the requested code.
_FAKE_CLAUDE_SCRIPT = r"""import json
import sys
fail = 0
big = 0
sleep_ms = 0
out_format = "json"
positional = []
args = sys.argv[1:]
i = 0
while i < len(args):
    a = args[i]
    if a == "--print":
        i += 1
    elif a == "--output-format" and i + 1 < len(args):
        out_format = args[i + 1]
        i += 2
    elif a == "--fail" and i + 1 < len(args):
        fail = int(args[i + 1])
        i += 2
    elif a == "--big" and i + 1 < len(args):
        big = int(args[i + 1])
        i += 2
    elif a == "--sleep" and i + 1 < len(args):
        sleep_ms = int(args[i + 1])
        i += 2
    else:
        positional.append(a)
        i += 1

if sleep_ms > 0:
    import time as _t
    _t.sleep(sleep_ms / 1000.0)

msg = " ".join(positional)
payload = {"result": msg, "fake": True}
if out_format == "json":
    sys.stdout.write(json.dumps(payload))
    if big > 0:
        sys.stdout.write("x" * big)
    sys.stdout.write("\n")
else:
    sys.stdout.write(msg + "\n")
if fail:
    sys.exit(fail)
sys.exit(0)
"""


@pytest.fixture
def fake_claude_binary(tmp_path: Path) -> str:
    """Write a fake `claude` CLI to tmp_path and return its absolute path.

    On Windows we generate a .cmd wrapper so the binary can be invoked as
    `binary --print ...` without python being on the search PATH that the
    adapter uses.
    """
    script = tmp_path / "fake_claude.py"
    script.write_text(_FAKE_CLAUDE_SCRIPT, encoding="utf-8")
    if sys.platform == "win32":
        runner = tmp_path / "fake_claude.cmd"
        runner.write_text(
            f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n',
            encoding="utf-8",
        )
    else:
        runner = tmp_path / "fake_claude.sh"
        runner.write_text(f"#!/bin/sh\n{sys.executable} {script} \"$@\"\n")
        runner.chmod(0o755)
    return str(runner)


def _make_registry(
    *,
    claude_binary: str | None = None,
    include_codex: bool = True,
) -> WorkerRegistry:
    """Build a registry with a real ClaudeCodeAdapter (and Codex for routing control)."""
    reg = WorkerRegistry()
    reg.register(
        ClaudeCodeAdapter(binary=claude_binary) if claude_binary
        else ClaudeCodeAdapter()
    )
    if include_codex:
        reg.register(CodexAdapter())
    return reg


def _make_scheduler(
    registry: WorkerRegistry,
    *,
    max_retries: int = 1,
    base_retry_delay_s: float = 0.001,
    memory: MemoryPersistence | None = None,
) -> AIOSScheduler:
    return AIOSScheduler(
        registry=registry,
        config=SchedulerConfig(
            max_concurrent=4,
            max_retries=max_retries,
            base_retry_delay_s=base_retry_delay_s,
        ),
        memory=memory,
    )


async def _wait_for_metrics(
    s: AIOSScheduler,
    *,
    expected_completed: int,
    timeout_s: float = 5.0,
) -> dict:
    """Poll scheduler.metrics() until expected completed count is reached."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        snap = s.metrics()
        if snap["completed"] + snap["failed"] >= expected_completed:
            return snap
        await asyncio.sleep(0.02)
    return s.metrics()


# ---------------------------------------------------------------------------
# 1. Direct adapter behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_claude_code_adapter_runs_real_binary(fake_claude_binary):
    """Inject a fake `claude` binary; verify subprocess runs and
    the artifact contains the binary's stdout as JSON."""
    adapter = ClaudeCodeAdapter(binary=fake_claude_binary)
    t = Task(goal_id="g-1", title="hello-claude", task_type=TaskType.MATH_CALC)
    art = await adapter.execute(t)
    assert art.task_id == t.id
    assert art.artifact_type == ArtifactType.CUSTOM
    assert art.label == "claude_code_result"
    assert art.inline_json["worker"] == "claude-code-adapter"
    assert art.inline_json["binary"] == fake_claude_binary
    assert art.inline_json["exit_code"] == 0
    # stdout contains the JSON payload the fake binary wrote
    assert "hello-claude" in art.inline_json["stdout"]
    # stub_fallback should be False
    assert art.inline_json["stub_fallback"] is False


@pytest.mark.asyncio
async def test_e2e_claude_code_adapter_handles_binary_exit_7(fake_claude_binary):
    """A binary that exits non-zero must still produce an artifact (not raise)."""
    # we cannot pass extra flags via ClaudeCodeAdapter, so we drive it via
    # execute() with title that the fake binary will treat as positional only.
    # The fake binary doesn't have a way to set --fail via positional args,
    # so we monkey-patch the runner instead.
    import aios_kernel.workers.claude_code_adapter as cca_mod

    class _FlakyRunner:
        def __init__(self, target):
            self._target = target

        async def run(self, cmd, env):
            # inject --fail 7 into the command
            return await self._target.run([cmd[0], "--fail", "7", *cmd[1:]], env)

    adapter = ClaudeCodeAdapter(binary=fake_claude_binary)
    adapter._runner = _FlakyRunner(cca_mod.SubprocessRunner())  # type: ignore[assignment]

    t = Task(goal_id="g-1", title="any", task_type=TaskType.MATH_CALC)
    art = await adapter.execute(t)
    assert art.inline_json["exit_code"] == 7
    assert art.label == "claude_code_result"


@pytest.mark.asyncio
async def test_e2e_claude_code_adapter_stub_fallback_when_binary_missing():
    """When the binary does not exist, adapter returns a stub_fallback artifact
    and does NOT raise FileNotFoundError."""
    adapter = ClaudeCodeAdapter(binary="definitely-not-a-real-binary-xyz123")
    t = Task(goal_id="g-1", title="anything", task_type=TaskType.MATH_CALC)
    art = await adapter.execute(t)
    assert art.label == "stub_fallback"
    assert art.inline_json["worker"] == "claude-code-adapter"
    assert art.inline_json["stub"] is True
    assert "not found" in art.inline_json["reason"]


@pytest.mark.asyncio
async def test_e2e_claude_code_adapter_truncates_large_output(fake_claude_binary):
    """stdout and stderr must be truncated to 4096 / 1024 bytes."""
    import aios_kernel.workers.claude_code_adapter as cca_mod

    class _BigRunner:
        def __init__(self, target):
            self._target = target

        async def run(self, cmd, env):
            return await self._target.run([cmd[0], "--big", "10000", *cmd[1:]], env)

    adapter = ClaudeCodeAdapter(binary=fake_claude_binary)
    adapter._runner = _BigRunner(cca_mod.SubprocessRunner())  # type: ignore[assignment]

    t = Task(goal_id="g-1", title="big", task_type=TaskType.MATH_CALC)
    art = await adapter.execute(t)
    assert len(art.inline_json["stdout"]) <= 4096
    assert len(art.inline_json["stderr"]) <= 1024


@pytest.mark.asyncio
async def test_e2e_claude_code_adapter_health_reports_binary_metadata(fake_claude_binary):
    adapter = ClaudeCodeAdapter(binary=fake_claude_binary)
    h = await adapter.health()
    assert h.worker_id == "claude-code-adapter"
    assert h.status == HealthStatus.HEALTHY
    assert h.metadata["binary"] == fake_claude_binary


@pytest.mark.asyncio
async def test_e2e_claude_code_adapter_cancel_is_noop(fake_claude_binary):
    """cancel() must not raise, even for unknown task_id."""
    adapter = ClaudeCodeAdapter(binary=fake_claude_binary)
    await adapter.cancel("nonexistent-task-id")  # no exception


@pytest.mark.asyncio
async def test_e2e_claude_code_adapter_warmup_shutdown_idempotent(fake_claude_binary):
    adapter = ClaudeCodeAdapter(binary=fake_claude_binary)
    await adapter.warmup()
    await adapter.warmup()  # idempotent
    await adapter.shutdown()
    await adapter.shutdown()  # idempotent


# ---------------------------------------------------------------------------
# 2. WorkerRegistry routing
# ---------------------------------------------------------------------------


def test_e2e_registry_routes_math_calc_to_claude_code(fake_claude_binary):
    reg = WorkerRegistry()
    reg.register(ClaudeCodeAdapter(binary=fake_claude_binary))
    reg.register(CodexAdapter())
    t = Task(goal_id="g-1", title="t", task_type=TaskType.MATH_CALC)
    assert reg.route(t).worker_id == "claude-code-adapter"


def test_e2e_registry_routes_via_preferred_worker(fake_claude_binary):
    reg = WorkerRegistry()
    reg.register(ClaudeCodeAdapter(binary=fake_claude_binary))
    reg.register(CodexAdapter())
    # worker= override beats type routing
    t = Task(
        goal_id="g-1", title="t",
        task_type=TaskType.FILE_SUMMARY,  # would route to codex
        worker="claude-code-adapter",       # override
    )
    assert reg.route(t).worker_id == "claude-code-adapter"


def test_e2e_registry_routes_string_format_to_codex_not_claude(fake_claude_binary):
    """Sanity check: with Codex registered first, the first round-robin
    route() call returns codex-adapter (proves ordering is respected)."""
    reg = WorkerRegistry()
    reg.register(CodexAdapter())                                 # idx 0
    reg.register(ClaudeCodeAdapter(binary=fake_claude_binary))   # idx 1
    t = Task(goal_id="g-1", title="t", task_type=TaskType.STRING_FORMAT)
    assert reg.route(t).worker_id == "codex-adapter"
    # next call goes to claude-code
    assert reg.route(t).worker_id == "claude-code-adapter"


def test_e2e_registry_4agent_team_includes_claude_code():
    """register_four_agent_team must include claude-code-adapter (idempotent)."""
    from aios_kernel.workers.adapters import register_four_agent_team

    reg = WorkerRegistry()
    register_four_agent_team(reg)
    assert "claude-code-adapter" in reg.list_ids()
    # idempotent
    register_four_agent_team(reg)
    assert "claude-code-adapter" in reg.list_ids()


# ---------------------------------------------------------------------------
# 3. AIOSScheduler dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_scheduler_dispatches_math_calc_to_claude_code(fake_claude_binary):
    """Submit a MATH_CALC task; verify it completes via claude-code-adapter."""
    reg = _make_registry(claude_binary=fake_claude_binary)
    s = _make_scheduler(reg, max_retries=0)
    await s.start()
    try:
        t = Task(goal_id="g-e2e", title="2+2=4", task_type=TaskType.MATH_CALC)
        run_id = await s.submit(t, priority=Priority.P1)
        snap = await _wait_for_metrics(s, expected_completed=1, timeout_s=5.0)
        assert snap["completed"] >= 1
        # run_id is no longer in _active (task done + popped), but completed=1
        # is the ground truth
        assert s._active.get(run_id) is None
    finally:
        await s.stop()


@pytest.mark.asyncio
async def test_e2e_scheduler_writes_audit_ledger_for_claude_code(
    fake_claude_binary, tmp_path: Path,
):
    """Verify the audit ledger records task_submitted + task_completed for
    the claude-code-adapter dispatch path."""
    ledger = tmp_path / "events.jsonl"
    state = tmp_path / "state.json"
    mem = MemoryPersistence(ledger_path=ledger, state_path=state)
    reg = _make_registry(claude_binary=fake_claude_binary)
    s = _make_scheduler(reg, memory=mem, max_retries=0)
    await s.start()
    try:
        t = Task(goal_id="g-audit", title="audit-task", task_type=TaskType.MATH_CALC)
        await s.submit(t, priority=Priority.P1)
        snap = await _wait_for_metrics(s, expected_completed=1, timeout_s=5.0)
        assert snap["completed"] >= 1
    finally:
        await s.stop()

    # ledger must contain at least submitted + completed
    events = mem.read_ledger()
    types = [e.get("type") for e in events]
    assert "task_submitted" in types
    completed = [e for e in events if e.get("type") == "task_completed"]
    assert completed, "expected at least one task_completed event"
    assert completed[0]["worker"] == "claude-code-adapter"


@pytest.mark.asyncio
async def test_e2e_scheduler_concurrent_claude_code_dispatches(fake_claude_binary):
    """Submit 8 MATH_CALC tasks; all should complete (within max_concurrent=4)."""
    reg = _make_registry(claude_binary=fake_claude_binary)
    s = _make_scheduler(reg, max_retries=0)
    await s.start()
    try:
        for i in range(8):
            t = Task(goal_id="g-conc", title=f"task-{i}", task_type=TaskType.MATH_CALC)
            await s.submit(t, priority=Priority.P1)

        snap = await _wait_for_metrics(s, expected_completed=8, timeout_s=15.0)
        assert snap["submitted"] == 8
        assert snap["completed"] == 8
        assert snap["dlq_size"] == 0
    finally:
        await s.stop()


@pytest.mark.asyncio
async def test_e2e_scheduler_circuit_breaker_opens_on_repeated_failures():
    """When the claude-code-adapter execute() keeps raising, after 5 consecutive
    failures the circuit must transition to OPEN and reject new tasks (DLQ)."""
    reg = WorkerRegistry()

    class _FailingAdapter:
        worker_id = "claude-code-adapter"
        call_count = 0

        async def execute(self, task):
            _FailingAdapter.call_count += 1
            raise RuntimeError("simulated claude-code failure")

        async def cancel(self, task_id): pass
        async def health(self):
            from datetime import UTC, datetime

            from aios_kernel.workers.base import HealthReport, HealthStatus
            return HealthReport(
                worker_id="claude-code-adapter", status=HealthStatus.HEALTHY,
                last_check_at=datetime.now(UTC),
            )
        async def warmup(self): pass
        async def shutdown(self): pass

    failing = _FailingAdapter()
    reg.register(failing)  # type: ignore[arg-type]
    s = AIOSScheduler(
        registry=reg,
        config=SchedulerConfig(
            max_concurrent=2, max_retries=0,
            base_retry_delay_s=0.001, dlq_max_size=100,
        ),
    )
    await s.start()
    try:
        # submit 5 tasks to trip the breaker (5 consecutive failures → OPEN)
        for i in range(5):
            t = Task(goal_id="g-cb", title=f"fail-{i}", task_type=TaskType.MATH_CALC)
            await s.submit(t, priority=Priority.P0)

        # wait for 5 failures
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if s.metrics()["failed"] >= 5:
                break
            await asyncio.sleep(0.05)

        # Circuit should now be OPEN
        assert s._breakers["claude-code-adapter"].state == CircuitState.OPEN
        # 5+ tasks must have failed and gone to DLQ
        assert s.metrics()["failed"] >= 5
        assert s.metrics()["dlq_size"] >= 5
        # circuit_opened counter incremented
        assert s.metrics()["circuit_opened"] >= 1
    finally:
        await s.stop()


@pytest.mark.asyncio
async def test_e2e_scheduler_metrics_after_claude_code_dispatch(fake_claude_binary):
    """Verify metrics snapshot includes avg_dispatch_latency_s
    after a claude-code-adapter execution."""
    reg = _make_registry(claude_binary=fake_claude_binary)
    s = _make_scheduler(reg, max_retries=0)
    await s.start()
    try:
        for i in range(3):
            t = Task(goal_id="g-m", title=f"t-{i}", task_type=TaskType.MATH_CALC)
            await s.submit(t, priority=Priority.P2)
        snap = await _wait_for_metrics(s, expected_completed=3, timeout_s=5.0)
        assert snap["submitted"] == 3
        assert snap["completed"] == 3
        # scheduler exposes avg_dispatch_latency_s (averaged over completed runs)
        assert snap["avg_dispatch_latency_s"] >= 0.0
    finally:
        await s.stop()


# ---------------------------------------------------------------------------
# 4. HTTP gateway integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_http_submit_routes_to_claude_code_adapter(fake_claude_binary, monkeypatch):
    from aios_kernel.gateway.auth import sign_jwt
    secret = "isolated-claude-test-secret-never-for-production"
    monkeypatch.setenv("AIOS_KERNEL_JWT_SECRET", secret)
    monkeypatch.delenv("AIOS_KERNEL_AUTH_REQUIRED", raising=False)
    headers = {"Authorization": "Bearer " + sign_jwt({"sub": "test-worker"}, secret.encode())}
    """Submit a task via HTTP gateway; the scheduler dispatches it to the
    claude-code-adapter and reports completed."""
    reg = _make_registry(claude_binary=fake_claude_binary, include_codex=False)
    s = _make_scheduler(reg, max_retries=0)
    await s.start()
    try:
        client = TestClient(create_app(s))
        r = client.post(
            "/tasks",
            json={"goal_id": "g-http", "title": "http-claude-task", "priority": "P1"},
            headers=headers,
        )
        assert r.status_code == 202
        r.json()["run_id"]  # smoke-check the response body

        # poll metrics until at least 1 completed
        snap = await _wait_for_metrics(s, expected_completed=1, timeout_s=5.0)
        assert snap["completed"] >= 1

        # metrics endpoint must show at least 1 completed
        mr = client.get("/metrics")
        assert mr.status_code == 200
        snap_http = mr.json()
        assert snap_http["completed"] >= 1
    finally:
        await s.stop()


@pytest.mark.asyncio
async def test_e2e_http_metrics_endpoint_reflects_claude_code_dispatch(fake_claude_binary, monkeypatch):
    from aios_kernel.gateway.auth import sign_jwt
    secret = "isolated-metrics-test-secret-never-for-production"
    monkeypatch.setenv("AIOS_KERNEL_JWT_SECRET", secret)
    monkeypatch.delenv("AIOS_KERNEL_AUTH_REQUIRED", raising=False)
    headers = {"Authorization": "Bearer " + sign_jwt({"sub": "test-worker"}, secret.encode())}
    """After multiple HTTP-submitted tasks, the metrics endpoint must reflect them."""
    reg = _make_registry(claude_binary=fake_claude_binary, include_codex=False)
    s = _make_scheduler(reg, max_retries=0)
    await s.start()
    try:
        client = TestClient(create_app(s))
        for i in range(3):
            r = client.post(
                "/tasks",
                json={"goal_id": "g-mh", "title": f"m-{i}", "priority": "P2"},
                headers=headers,
            )
            assert r.status_code == 202
        # wait
        await _wait_for_metrics(s, expected_completed=3, timeout_s=5.0)
        mr = client.get("/metrics")
        snap_http = mr.json()
        assert snap_http["submitted"] == 3
        assert snap_http["completed"] == 3
    finally:
        await s.stop()


# ---------------------------------------------------------------------------
# 5. MCP integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_mcp_submit_task_dispatches_through_scheduler(fake_claude_binary):
    """MCP tools/call must dispatch a task through the scheduler."""
    reg = _make_registry(claude_binary=fake_claude_binary, include_codex=False)
    s = _make_scheduler(reg, max_retries=0)
    srv = MCPServer(s)
    await s.start()
    try:
        res = await srv.handle_tools_call(
            "aios_submit_task",
            {"goal_id": "g-mcp-c", "title": "mcp-claude", "priority": "P1"},
        )
        assert "submitted" in res["content"][0]["text"]
        snap = await _wait_for_metrics(s, expected_completed=1, timeout_s=5.0)
        assert snap["completed"] >= 1
        # metrics via MCP
        res_m = await srv.handle_tools_call("aios_get_metrics", {})
        assert res_m["content"][0]["text"]
    finally:
        await s.stop()


# ---------------------------------------------------------------------------
# 6. End-to-end full pipeline (gateway -> scheduler -> adapter -> audit)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_full_pipeline_4_module_claude_code(
    fake_claude_binary, tmp_path: Path, monkeypatch,
):
    from aios_kernel.gateway.auth import sign_jwt
    secret = "isolated-pipeline-test-secret-never-for-production"
    monkeypatch.setenv("AIOS_KERNEL_JWT_SECRET", secret)
    monkeypatch.delenv("AIOS_KERNEL_AUTH_REQUIRED", raising=False)
    headers = {"Authorization": "Bearer " + sign_jwt({"sub": "test-worker"}, secret.encode())}
    """Full R1503 §2 e2e: HTTP submit -> scheduler.submit -> registry.route
    (picks claude-code-adapter) -> ClaudeCodeAdapter.execute (real binary)
    -> audit ledger entry."""
    ledger = tmp_path / "events.jsonl"
    state = tmp_path / "state.json"
    mem = MemoryPersistence(ledger_path=ledger, state_path=state)
    reg = _make_registry(claude_binary=fake_claude_binary, include_codex=False)
    s = _make_scheduler(reg, memory=mem, max_retries=0)
    await s.start()
    try:
        client = TestClient(create_app(s))
        r = client.post(
            "/tasks",
            json={"goal_id": "g-pipe", "title": "pipeline-ok", "priority": "P0"},
            headers=headers,
        )
        assert r.status_code == 202
        run_id = r.json()["run_id"]
        snap = await _wait_for_metrics(s, expected_completed=1, timeout_s=5.0)
        assert snap["completed"] >= 1
    finally:
        await s.stop()

    # Verify the audit chain is intact
    events = mem.read_ledger()
    types = [e.get("type") for e in events]
    assert "task_submitted" in types
    assert "task_completed" in types

    # Verify the completed event was recorded by the claude-code-adapter
    completed = [e for e in events if e.get("type") == "task_completed"]
    assert completed[0]["worker"] == "claude-code-adapter"
    assert completed[0]["latency_s"] >= 0.0
    # And the submitted event references the same run_id
    submitted = [e for e in events if e.get("type") == "task_submitted"]
    assert submitted[0]["run_id"] == run_id


@pytest.mark.asyncio
async def test_e2e_artifact_returned_from_claude_code_adapter(fake_claude_binary):
    """Verify the artifact structure ClaudeCodeAdapter produces is well-formed
    (task_id matches, label is claude_code_result or stub_fallback, has
    inline_json with expected keys)."""
    adapter = ClaudeCodeAdapter(binary=fake_claude_binary)
    t = Task(goal_id="g-art", title="artifact-test", task_type=TaskType.MATH_CALC)
    art: Artifact = await adapter.execute(t)
    assert isinstance(art, Artifact)
    assert art.task_id == t.id
    assert art.label in ("claude_code_result", "stub_fallback")
    assert art.inline_json is not None
    for key in ("worker", "binary", "exit_code", "stdout", "stderr"):
        assert key in art.inline_json


# ---------------------------------------------------------------------------
# 7. Stub fallback e2e via scheduler (binary missing path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_scheduler_dispatch_with_missing_binary(tmp_path: Path):
    """When ClaudeCodeAdapter is configured with a non-existent binary, the
    scheduler must still mark the task as completed (via stub_fallback)."""
    ledger = tmp_path / "events.jsonl"
    state = tmp_path / "state.json"
    mem = MemoryPersistence(ledger_path=ledger, state_path=state)
    reg = WorkerRegistry()
    reg.register(ClaudeCodeAdapter(binary="nonexistent-binary-xyz"))
    s = _make_scheduler(reg, memory=mem, max_retries=0)
    await s.start()
    try:
        t = Task(goal_id="g-stub", title="stub-task", task_type=TaskType.MATH_CALC)
        await s.submit(t, priority=Priority.P1)
        snap = await _wait_for_metrics(s, expected_completed=1, timeout_s=5.0)
        # even with stub fallback, scheduler records it as completed
        assert snap["completed"] >= 1
        # the audit ledger has the completion
        events = mem.read_ledger()
        completed = [e for e in events if e.get("type") == "task_completed"]
        assert completed and completed[0]["worker"] == "claude-code-adapter"
    finally:
        await s.stop()
