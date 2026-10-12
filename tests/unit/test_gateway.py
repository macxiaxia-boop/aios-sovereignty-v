"""test_gateway.py - Tests for gateway/http + mcp + auth (R1503-007/008/009)."""
from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from aios_kernel.gateway.auth import (
    RateLimiter,
    sign_jwt,
    verify_jwt,
    InvalidToken,
)
from aios_kernel.gateway.http import create_app
from aios_kernel.gateway.mcp import MCPServer
from aios_kernel.scheduler import AIOSScheduler, Priority
from aios_kernel.workers.base import HealthReport, HealthStatus, WorkerAdapter
from aios_kernel.workers.registry import WorkerRegistry


# ----- test helpers -------------------------------------------------------


class _Stub(WorkerAdapter):
    def __init__(self, worker_id):
        self.worker_id = worker_id

    async def execute(self, task):
        from aios_kernel.domain.artifact import Artifact, ArtifactType
        return Artifact(task_id=task.id, artifact_type=ArtifactType.CUSTOM,
                       label="ok", inline_json={"w": self.worker_id})

    async def cancel(self, task_id): return None
    async def health(self):
        return HealthReport(worker_id=self.worker_id, status=HealthStatus.HEALTHY,
                          last_check_at=__import__("datetime").datetime.now(__import__("datetime").UTC))
    async def warmup(self): return None
    async def shutdown(self): return None


def _make_scheduler():
    reg = WorkerRegistry()
    reg.register(_Stub("stub"))
    s = AIOSScheduler(registry=reg, config=__import__("aios_kernel.scheduler", fromlist=["SchedulerConfig"]).SchedulerConfig(max_concurrent=1))
    return s


# ----- HTTP ---------------------------------------------------------------


def test_http_health():
    s = _make_scheduler()
    client = TestClient(create_app(s))
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True


def test_http_metrics():
    s = _make_scheduler()
    client = TestClient(create_app(s))
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "submitted" in body
    assert "completed" in body


def test_http_submit_task():
    s = _make_scheduler()
    client = TestClient(create_app(s))
    r = client.post("/tasks", json={"goal_id": "g1", "title": "t1"})
    assert r.status_code == 202
    body = r.json()
    assert body["run_id"].startswith("run-")
    assert "task_id" in body


def test_http_submit_invalid_priority():
    s = _make_scheduler()
    client = TestClient(create_app(s))
    # Pydantic enforces the pattern in the request model → 422 before our handler.
    r = client.post("/tasks", json={"goal_id": "g1", "title": "t1", "priority": "P9"})
    assert r.status_code == 422


# ----- MCP ---------------------------------------------------------------


def test_mcp_initialize():
    s = _make_scheduler()
    srv = MCPServer(s)
    result = srv.handle_initialize({})
    assert result["serverInfo"]["name"] == "aios-mcp"


def test_mcp_tools_list():
    s = _make_scheduler()
    srv = MCPServer(s)
    res = srv.handle_tools_list()
    tool_names = {t["name"] for t in res["tools"]}
    assert {"aios_submit_task", "aios_get_task_status", "aios_get_metrics", "aios_get_health"} <= tool_names


@pytest.mark.asyncio
async def test_mcp_call_get_health():
    s = _make_scheduler()
    srv = MCPServer(s)
    res = await srv.handle_tools_call("aios_get_health", {})
    assert "ok" in res["content"][0]["text"]


@pytest.mark.asyncio
async def test_mcp_call_submit_task():
    s = _make_scheduler()
    srv = MCPServer(s)
    res = await srv.handle_tools_call(
        "aios_submit_task",
        {"goal_id": "g1", "title": "t1"},
    )
    assert "submitted" in res["content"][0]["text"]


@pytest.mark.asyncio
async def test_mcp_call_unknown_tool():
    s = _make_scheduler()
    srv = MCPServer(s)
    res = await srv.handle_tools_call("nonexistent", {})
    assert res.get("isError") is True


@pytest.mark.asyncio
async def test_mcp_request_dispatch_unknown_method():
    s = _make_scheduler()
    srv = MCPServer(s)
    res = await srv.handle_request({"jsonrpc": "2.0", "id": 1, "method": "nope"})
    assert "error" in res


# ----- AUTH ---------------------------------------------------------------


def test_jwt_roundtrip():
    secret = b"hunter2"
    tok = sign_jwt({"sub": "alice"}, secret)
    claims = verify_jwt(tok, secret)
    assert claims["sub"] == "alice"


def test_jwt_invalid_signature():
    secret = b"hunter2"
    other = b"hunter3"
    tok = sign_jwt({"sub": "alice"}, secret)
    with pytest.raises(InvalidToken):
        verify_jwt(tok, other)


def test_jwt_expired():
    secret = b"hunter2"
    tok = sign_jwt({"sub": "alice", "exp": int(time.time()) - 1}, secret, ttl_s=0)
    with pytest.raises(InvalidToken):
        verify_jwt(tok, secret)


def test_rate_limiter_basic():
    rl = RateLimiter(capacity=3, refill_rate=0)  # no refill
    assert rl.try_acquire("w")
    assert rl.try_acquire("w")
    assert rl.try_acquire("w")
    assert not rl.try_acquire("w")


def test_rate_limiter_refill():
    rl = RateLimiter(capacity=1, refill_rate=10)
    assert rl.try_acquire("w")
    assert not rl.try_acquire("w")
    time.sleep(0.2)
    assert rl.try_acquire("w")


def test_rate_limiter_per_worker():
    rl = RateLimiter(capacity=1, refill_rate=0)
    assert rl.try_acquire("a")
    assert rl.try_acquire("b")
    assert not rl.try_acquire("a")
    assert not rl.try_acquire("b")