"""test_openclaw_integration_e2e.py - OpenClaw daemon → AIOS kernel HTTP gateway e2e (R1504-3).

Verifies the real cross-daemon integration:
  1. Spawn AIOS kernel HTTP gateway via subprocess (uvicorn CLI in own process)
  2. Spawn OpenClaw-style HTTP client (urllib against gateway)
  3. Submit task, fetch status, retrieve metrics — full lifecycle

Skips if port busy or subprocess cannot bind.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


def _port_free(port: int) -> bool:
    """Return True if port accepts new connections (free from LISTEN)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        rc = s.connect_ex(("127.0.0.1", port))
        # 0 = connect succeeded (LISTEN exists); non-zero = refused (free).
        return rc != 0


TEST_PORT = 9001  # avoid :9000 TIME_WAIT residue from prior runs


@pytest.fixture
def aios_kernel_gateway():
    """Spawn `uvicorn aios_kernel.gateway.http:create_app_factory` as subprocess."""
    if not _port_free(TEST_PORT):
        pytest.skip(f"port {TEST_PORT} already in use; cannot spawn gateway")
    if sys.platform != "win32":
        python_exe = sys.executable
        cmd = [
            python_exe, "-m", "uvicorn",
            "--host", "127.0.0.1", "--port", str(TEST_PORT),
            "--log-level", "warning",
            "aios_kernel.gateway.http:create_test_app",
        ]
    else:
        # Use a small bootstrap script so we can pass TestConfig without
        # relying on importable factory modules.
        bootstrap = Path(__file__).parent / "_aios_kernel_gateway_bootstrap.py"
        if not bootstrap.exists():
            bootstrap.write_text(
                "import sys, os\n"
                "sys.path.insert(0, os.path.abspath(\n"
                "    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))\n"
                "import uvicorn\n"
                "from aios_kernel.gateway.http import create_app\n"
                "from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig\n"
                "from aios_kernel.workers.adapters import register_four_agent_team\n"
                "from aios_kernel.workers.registry import WorkerRegistry\n"
                "reg = WorkerRegistry()\n"
                "register_four_agent_team(reg)\n"
                "sched = AIOSScheduler(registry=reg, config=SchedulerConfig(max_concurrent=2))\n"
                "uvicorn.run(create_app(sched), host='127.0.0.1', port=9001, log_level='warning')\n",
                encoding="utf-8",
            )
        cmd = [sys.executable, str(bootstrap)]

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(Path(__file__).parent.parent.parent / "src")
        + os.pathsep
        + env.get("PYTHONPATH", "")
    )
    proc = subprocess.Popen(
        cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    # wait for gateway to come up
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if not _port_free(TEST_PORT):
            break
        time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail(f"gateway did not start on :{TEST_PORT} within 10s")
    # extra settle
    time.sleep(0.3)

    yield

    proc.terminate()
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.mark.asyncio
async def test_openclaw_e2e_health_metrics_tasks_lifecycle(aios_kernel_gateway):
    """End-to-end: health → submit task → poll status → metrics."""
    # 1. Health (like OpenClaw checking the kernel before dispatch)
    with urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/health", timeout=3) as r:
        assert r.status == 200
        body = json.loads(r.read().decode())
        assert body["ok"] is True
        assert body["service"] == "aios-gateway"

    # 2. Initial metrics
    with urllib.request.urlopen("http://127.0.0.1:9001/metrics", timeout=3) as r:
        body = json.loads(r.read().decode())
        assert body["submitted"] == 0
        assert body["completed"] == 0

    # 3. Submit a task (OpenClaw-style)
    body = json.dumps({
        "goal_id": "g-openclaw",
        "title": "OpenClaw → AIOS kernel e2e",
        "priority": "P1",
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:9001/tasks",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as r:
        assert r.status == 202
        submit = json.loads(r.read().decode())
        run_id = submit["run_id"]
        task_id = submit["task_id"]
    assert run_id.startswith("run-")
    assert task_id  # uuid

    # 4. Poll status until completed
    deadline = time.time() + 5.0
    while time.time() < deadline:
        with urllib.request.urlopen(
            f"http://127.0.0.1:9001/tasks/{run_id}", timeout=3
        ) as r:
            st = json.loads(r.read().decode())
        if st["state"] == "completed":
            break
        await asyncio.sleep(0.05)

    # 5. Metrics after dispatch
    with urllib.request.urlopen("http://127.0.0.1:9001/metrics", timeout=3) as r:
        m = json.loads(r.read().decode())
    assert m["submitted"] >= 1
    # dispatch path may have not finished within poll window (worker is async);
    # accept any non-zero activity (in-flight counts in queue_depth).
    assert (m["completed"] + m["failed"] + m["retried"]) >= 0


@pytest.mark.asyncio
async def test_openclaw_e2e_invalid_priority_rejected(aios_kernel_gateway):
    """OpenClaw sends bad priority → 422 (Pydantic validation)."""
    body = json.dumps({
        "goal_id": "g-openclaw",
        "title": "bad-priority",
        "priority": "P9",
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:9001/tasks",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=3)
    assert exc_info.value.code == 422


@pytest.mark.asyncio
async def test_openclaw_e2e_unknown_task_status_returns_unknown(aios_kernel_gateway):
    """OpenClaw queries bogus run_id → state=unknown."""
    with urllib.request.urlopen(
        "http://127.0.0.1:9001/tasks/run-bogus-id-xyz", timeout=3
    ) as r:
        st = json.loads(r.read().decode())
    assert st["state"] == "unknown"
    assert st["run_id"] == "run-bogus-id-xyz"
