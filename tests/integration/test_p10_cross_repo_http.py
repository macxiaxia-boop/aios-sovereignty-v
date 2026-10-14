"""Real loopback HTTP smoke: AIOS worker calls EXISTING CloudTech V4 ASGI.

This test requires CLOUDTECH_V4_CHECKOUT to point to the separate repository
checkout, so ordinary isolated unit runs skip it. GitHub cross-repo CI
runs it unconditionally with this environment variable.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from aios_kernel.domain.task import Task
from aios_kernel.workers.cloudtech_v4_adapter import CloudTechV4Adapter


@pytest.mark.asyncio
async def test_real_http_to_cloudtech_v4_backend():
    checkout = os.environ.get("CLOUDTECH_V4_CHECKOUT")
    if not checkout:
        pytest.skip("external repository checkout required for cross-repo test")
    root = Path(checkout).resolve()
    if not (root / "api/v4/asgi.py").is_file():
        pytest.fail("CloudTech V4 ASGI source missing in checkout")

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root)
    env["V4_ENV"] = "development"  # loopback test only; never internet exposed
    env.pop("V4_JWT_SECRET", None)
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "api.v4.asgi:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        cwd=str(root), env=env, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE, text=True,
    )
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            for _ in range(100):
                if proc.poll() is not None:
                    error = proc.stderr.read() if proc.stderr else ""
                    pytest.fail(f"CloudTech V4 ASGI exited before ready: {error[-2000:]}")
                try:
                    response = await client.get(base_url + "/v4/workpaths/capabilities")
                    if response.status_code == 200:
                        break
                except (httpx.ConnectError, httpx.ReadTimeout):
                    pass
                time.sleep(0.07)
            else:
                pytest.fail("CloudTech V4 loopback API did not become ready")

        worker = CloudTechV4Adapter(base_url=base_url)
        try:
            task = Task(
                goal_id="p10-loopback", title="authorized loopback-only contract",
                worker="cloudtech-v4-adapter",
                input_payload={
                    "action": "create_and_execute_local",
                    "tenant_id": "isolated-ci-tenant",
                    "path_id": "WP-BLOGGER-RESEARCH",
                    "input_bindings": {
                        "homepage_url": "https://example.com/creator?cursor=1",
                        "target_industry": "装修",
                    },
                },
            )
            artifact = await worker.execute(task)
            result = artifact.inline_json
            assert result["business_validated"] is False
            assert result["data"]["preflight"]["execution_ready"] is False
            local = result["data"]["local_execution"]
            assert local["executed_nodes"] == ["url_normalize"]
            assert local["blocked_at"]["reason"] == "MOCK_ONLY"
            assert local["external_calls"] == 0
            assert local["charged_cents"] == 0
            assert len(artifact.hash_sha256) == 64
        finally:
            await worker.shutdown()
    finally:
        proc.terminate()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
