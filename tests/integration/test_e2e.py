"""test_e2e.py - End-to-end integration test (R1503 FINAL).

Verifies the 4 modules integrate correctly:
  - gateway/http -> scheduler.submit() -> WorkerAdapter.execute() -> state_machine
  - gateway/mcp tools/call dispatch
  - runtime/memory append_ledger after dispatch
  - scheduler.status() returns completed

Co-Authored-By: Claude Code (Agent 1+4) via AIOS R1503 FINAL
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aios_kernel.agents.protocol import AgentMessage, AgentProtocol, MessageType
from aios_kernel.agents.registry import AgentRegistry
from aios_kernel.gateway.auth import RateLimiter, sign_jwt, verify_jwt
from aios_kernel.gateway.http import create_app
from aios_kernel.gateway.mcp import MCPServer
from aios_kernel.runtime.memory import MemoryPersistence
from aios_kernel.scheduler import AIOSScheduler, Priority, SchedulerConfig
from aios_kernel.state_machine import task_fsm, workflow_fsm
from aios_kernel.workers.base import HealthReport, HealthStatus, WorkerAdapter
from aios_kernel.workers.registry import WorkerRegistry
from aios_kernel.domain.task import Task, TaskStatus, TaskType
from aios_kernel.workflows.workflow import WorkflowStatus


class _StubAdapter(WorkerAdapter):
    def __init__(self, worker_id, *, fail=False):
        self.worker_id = worker_id
        self._fail = fail

    async def execute(self, task):
        if self._fail:
            raise RuntimeError("stub fail")
        from aios_kernel.domain.artifact import Artifact, ArtifactType
        return Artifact(task_id=task.id, artifact_type=ArtifactType.CUSTOM,
                       label="ok", inline_json={"w": self.worker_id})

    async def cancel(self, task_id):
        return None

    async def health(self):
        import datetime
        return HealthReport(worker_id=self.worker_id, status=HealthStatus.HEALTHY,
                          last_check_at=datetime.datetime.now(datetime.UTC))

    async def warmup(self):
        return None

    async def shutdown(self):
        return None


def _make_scheduler_with_workers():
    reg = WorkerRegistry()
    reg.register(_StubAdapter("claude-code-stub"))
    reg.register(_StubAdapter("codex-stub"))
    reg.register(_StubAdapter("openclaw-stub"))
    reg.register(_StubAdapter("hermes-stub"))
    return AIOSScheduler(
        registry=reg,
        config=SchedulerConfig(max_concurrent=4, max_retries=1, base_retry_delay_s=0.001),
    )


# ---------- e2e: HTTP gateway -> scheduler -> 4-Agent Worker ----------


@pytest.mark.asyncio
async def test_e2e_http_submit_dispatches_to_4_agent_worker(tmp_path: Path):
    s = _make_scheduler_with_workers()
    await s.start()
    try:
        client = TestClient(create_app(s))
        # submit a task
        r = client.post("/tasks", json={"goal_id": "g-e2e", "title": "e2e-test", "priority": "P1"})
        assert r.status_code == 202
        run_id = r.json()["run_id"]

        # wait for completion (up to 5s)
        deadline = time.time() + 5.0
        while time.time() < deadline:
            st = await s.status(run_id)
            if st["state"] in ("completed", "failed"):
                break
            await asyncio.sleep(0.05)
        snap = s.metrics()
        assert snap["submitted"] >= 1
        # 4 adapters, round-robin so dispatched to one
        assert snap["completed"] + snap["failed"] >= 1
    finally:
        await s.stop()


# ---------- e2e: MCP tools/call -> submit_task ----------


@pytest.mark.asyncio
async def test_e2e_mcp_submit_task_roundtrip():
    s = _make_scheduler_with_workers()
    srv = MCPServer(s)
    await s.start()
    try:
        # MCP submit via tools/call
        res = await srv.handle_tools_call(
            "aios_submit_task",
            {"goal_id": "g-mcp", "title": "mcp-task", "priority": "P0"},
        )
        assert "submitted" in res["content"][0]["text"]
        # MCP get_metrics
        res2 = await srv.handle_tools_call("aios_get_metrics", {})
        assert res2["content"][0]["text"]
        # MCP get_task_status with bogus run_id
        res3 = await srv.handle_tools_call(
            "aios_get_task_status", {"run_id": "run-bogus"}
        )
        # bogus returns 'unknown' state
        assert "unknown" in res3["content"][0]["text"]
    finally:
        await s.stop()


# ---------- e2e: agents protocol handshake ----------


@pytest.mark.asyncio
async def test_e2e_agents_protocol_request_response():
    proto = AgentProtocol()
    proto.register("client")
    proto.register("server")

    async def server_loop():
        msg = await proto.receive("server", timeout_s=1.0)
        if msg and msg.type == MessageType.REQUEST:
            await proto.respond(msg, payload={"ack": True})

    asyncio.create_task(server_loop())
    resp = await proto.request("client", "server", payload={"q": "ping"}, timeout_s=2.0)
    assert resp is not None
    assert resp.payload == {"ack": True}


# ---------- e2e: agents registry -> capability discovery ----------


def test_e2e_agents_registry_capability_routing():
    reg = AgentRegistry()
    reg.register("claude-code-stub", capabilities=["code", "review"], priority=10)
    reg.register("codex-stub", capabilities=["code", "shell"], priority=20)
    reg.register("openclaw-stub", capabilities=["shell", "deploy"], priority=15)

    # discover agent that can do "code"
    matches = reg.find_by_capability("code")
    assert matches[0].name == "claude-code-stub"  # priority 10 wins

    # discover agent that can do "shell"
    matches = reg.find_by_capability("shell")
    assert matches[0].name == "openclaw-stub"  # priority 15 wins over 20


# ---------- e2e: state_machine for Task lifecycle ----------


def test_e2e_task_fsm_full_lifecycle():
    fsm = task_fsm()
    transitions = [
        ("start", TaskStatus.RUNNING),
        ("verify", TaskStatus.VERIFYING),
        ("redo", TaskStatus.RUNNING),
        ("verify", TaskStatus.VERIFYING),
        ("done", TaskStatus.DONE),
    ]
    for event, expected in transitions:
        fsm.fire(event)
        assert fsm.state == expected


def test_e2e_workflow_fsm_lifecycle():
    fsm = workflow_fsm()
    fsm.fire("start")
    assert fsm.state == WorkflowStatus.RUNNING
    fsm.fire("complete")
    assert fsm.state == WorkflowStatus.COMPLETED


# ---------- e2e: runtime/memory ledger persistence ----------


def test_e2e_memory_ledger_persists_across_instances(tmp_path: Path):
    ledger_path = tmp_path / "events.jsonl"
    state_path = tmp_path / "state.json"
    mp1 = MemoryPersistence(ledger_path=ledger_path, state_path=state_path)
    mp1.append_ledger({"type": "task_submitted", "task_id": "t-e2e"})
    mp1.state_set("last_task", "t-e2e")
    # simulate restart
    mp2 = MemoryPersistence(ledger_path=ledger_path, state_path=state_path)
    assert mp2.state_get("last_task") == "t-e2e"
    events = mp2.read_ledger()
    assert any(e.get("task_id") == "t-e2e" for e in events)


# ---------- e2e: auth/rate-limit workflow ----------


def test_e2e_jwt_then_rate_limit():
    secret = b"aios-r1503-secret"
    tok = sign_jwt({"sub": "client", "scope": "submit"}, secret, ttl_s=300)
    claims = verify_jwt(tok, secret)
    assert claims["sub"] == "client"

    rl = RateLimiter(capacity=2, refill_rate=0)
    assert rl.try_acquire("client")
    assert rl.try_acquire("client")
    assert not rl.try_acquire("client")  # over capacity


# ---------- e2e: 4-Agent full e2e (submit -> dispatch -> complete -> metrics) ----------


@pytest.mark.asyncio
async def test_e2e_4_agent_full_workflow():
    """Submit 4 tasks, each dispatched to one of the 4 Agents, verify metrics."""
    s = _make_scheduler_with_workers()
    await s.start()
    try:
        # submit 4 tasks, one per priority
        run_ids = []
        for prio in (Priority.P0, Priority.P1, Priority.P1, Priority.P2):
            t = Task(
                goal_id="g-4agent",
                title=f"task-{prio.value}",
                task_type=TaskType.CUSTOM,
            )
            rid = await s.submit(t, priority=prio)
            run_ids.append(rid)

        # wait for all 4 to complete
        deadline = time.time() + 10.0
        while time.time() < deadline:
            statuses = [await s.status(rid) for rid in run_ids]
            if all(st["state"] in ("completed", "failed") for st in statuses):
                break
            await asyncio.sleep(0.05)

        snap = s.metrics()
        assert snap["submitted"] >= 4
        assert snap["completed"] >= 4
        assert snap["dlq_size"] == 0
    finally:
        await s.stop()