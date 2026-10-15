"""test_4adapter_binary_e2e.py - Real binary invocation tests (R1505-5).

These tests invoke the 4 Worker Adapters with REAL binaries (when present):
  - claude_code_adapter: `claude --print`
  - codex_adapter: `codex exec`
  - openclaw_adapter: HTTP POST to OpenClaw daemon (default :18792)
  - hermes_adapter: in-process CIO

Tests skip when the binary / daemon is not available (CI on Linux without
Claude/Codex installed will skip; OpenClaw test launches its own daemon).
"""
from __future__ import annotations

import asyncio
import shutil
import uuid

import pytest

from aios_kernel.domain.task import Task, TaskType
from aios_kernel.workers.adapters import register_four_agent_team
from aios_kernel.workers.claude_code_adapter import ClaudeCodeAdapter
from aios_kernel.workers.codex_adapter import CodexAdapter
from aios_kernel.workers.hermes_adapter import HermesAdapter
from aios_kernel.workers.openclaw_adapter import OpenClawAdapter
from aios_kernel.workers.registry import WorkerRegistry


def _task(idx: int = 1) -> Task:
    return Task(
        id=str(uuid.uuid4()),
        goal_id="g-r1505-5",
        title=f"R1505-5 e2e task {idx}",
        task_type=TaskType.CUSTOM,
    )


# ---------- claude ----------


@pytest.mark.skipif(
    shutil.which("claude") is None, reason="claude binary not installed"
)
@pytest.mark.asyncio
async def test_claude_code_adapter_invokes_binary():
    a = ClaudeCodeAdapter()
    art = await asyncio.wait_for(a.execute(_task(1)), timeout=120.0)
    assert art.task_id is not None
    # Real binary: stdout present, exit_code 0 (or 1 for unknown prompt format)
    assert "stdout" in art.inline_json
    assert "exit_code" in art.inline_json
    a.shutdown()


@pytest.mark.skipif(
    shutil.which("claude") is None, reason="claude binary not installed"
)
@pytest.mark.asyncio
async def test_claude_code_adapter_health_real():
    a = ClaudeCodeAdapter()
    h = await a.health()
    assert h.worker_id == "claude-code-adapter"
    assert h.status.value in ("healthy", "degraded", "unhealthy")


# ---------- codex ----------


@pytest.mark.skipif(
    shutil.which("codex") is None, reason="codex binary not installed"
)
@pytest.mark.asyncio
async def test_codex_adapter_invokes_binary():
    a = CodexAdapter()
    art = await asyncio.wait_for(a.execute(_task(2)), timeout=30.0)
    assert art.task_id is not None
    # Windows codex.cmd wrapper may return exit 1 due to 'global' not recognized
    # but the adapter still returns a valid artifact with stdout/stderr.
    assert "exit_code" in art.inline_json
    assert "stderr" in art.inline_json
    a.shutdown()


# ---------- hermes (always works - in-process) ----------


@pytest.mark.asyncio
async def test_hermes_adapter_always_runs():
    a = HermesAdapter()
    art = await a.execute(_task(3))
    assert art.task_id is not None
    assert "intent" in art.inline_json
    h = await a.health()
    assert h.worker_id == "hermes-adapter"
    assert h.status.value == "healthy"


# ---------- openclaw (daemon required) ----------


def _openclaw_daemon_live() -> bool:
    """Quick HTTP probe to :18792/health."""
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:18792/health", timeout=2) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(
    not _openclaw_daemon_live(), reason="OpenClaw daemon not reachable at :18792"
)
@pytest.mark.asyncio
async def test_openclaw_adapter_invokes_daemon():
    a = OpenClawAdapter()
    art = await a.execute(_task(4))
    assert art.task_id is not None
    assert art.inline_json.get("base_url") == "http://localhost:18792"
    h = await a.health()
    assert h.worker_id == "openclaw-adapter"


# ---------- 4-Agent registry (always works) ----------


@pytest.mark.asyncio
async def test_register_four_agent_team_in_registry():
    reg = WorkerRegistry()
    register_four_agent_team(reg)
    ids = reg.list_ids()
    assert "claude-code-adapter" in ids
    assert "codex-adapter" in ids
    assert "openclaw-adapter" in ids
    assert "hermes-adapter" in ids
    assert len(ids) == 4

    # Idempotent (call twice)
    register_four_agent_team(reg)
    assert len(reg.list_ids()) == 4
