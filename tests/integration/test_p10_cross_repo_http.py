"""Real loopback HTTP smoke: AIOS worker calls EXISTING CloudTech V4 ASGI.

This test requires CLOUDTECH_V4_CHECKOUT to point to the separate repository
checkout, so ordinary isolated unit runs skip it. GitHub cross-repo CI
runs it unconditionally with this environment variable.
"""
from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from aios_kernel.domain.task import Task
from aios_kernel.gateway.auth import sign_jwt
from aios_kernel.workers.cloudtech_v4_adapter import CloudTechV4Adapter


@pytest.mark.asyncio
async def test_real_http_to_cloudtech_v4_backend(monkeypatch):
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
    # Exercise signed tenancy on the actual CloudTech server, not dev bypass.
    ct_secret = "isolated-ci-signing-secret-for-cloudtech-v4-2026"
    env["V4_ENV"] = "production"
    env["V4_JWT_SECRET"] = ct_secret
    monkeypatch.setenv("CLOUDTECH_V4_JWT_SECRET", ct_secret)
    monkeypatch.setenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", "1")
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



def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_uvicorn(target: str, port: int, *, cwd: Path, env: dict):
    return subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", target,
            "--host", "127.0.0.1", "--port", str(port),
        ],
        cwd=str(cwd), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )


async def _health_url(client, url: str, process) -> None:
    for _ in range(150):
        if process.poll() is not None:
            err = process.stderr.read() if process.stderr else ""
            pytest.fail(f"server stopped before ready: {err[-2500:]}")
        try:
            response = await client.get(url)
            if response.status_code == 200:
                return
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        await asyncio.sleep(.08)
    pytest.fail(f"server was not ready at {url}")


def _stop_process(proc) -> None:
    proc.terminate()
    try:
        proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate(timeout=5)


@pytest.mark.asyncio
async def test_two_real_services_persist_artifact_across_gateway_restart(tmp_path):
    checkout = os.environ.get("CLOUDTECH_V4_CHECKOUT")
    if not checkout:
        pytest.skip("cross repository checkout required")
    cloudtech = Path(checkout).resolve()
    if not (cloudtech / "api/v4/asgi.py").is_file():
        pytest.fail("real CloudTech ASGI entry missing")
    aios_root = Path(__file__).resolve().parents[2]
    ct_port, aios_port = _port(), _port()
    ct_url, aios_url = (
        f"http://127.0.0.1:{ct_port}", f"http://127.0.0.1:{aios_port}"
    )
    secret = b"p10-localhost-only-dual-service-secret-12345678"
    tenant = "dual-service-ci"
    bearer = sign_jwt({"sub": "operator", "tenant_id": tenant}, secret)
    headers = {"Authorization": f"Bearer {bearer}"}

    ct_env = dict(os.environ)
    ct_env["PYTHONPATH"] = str(cloudtech)
    ct_secret = b"isolated-ci-cloudtech-service-signing-2026-tenant"
    ct_env["V4_ENV"] = "production"
    ct_env["V4_JWT_SECRET"] = ct_secret.decode()
    ct_env["CLOUDTECH_V4_SQLITE_PATH"] = str(tmp_path / "cloudtech-v4.db")
    aios_env = dict(os.environ)
    aios_env["PYTHONPATH"] = str(aios_root / "src")
    aios_env.update({
        "AIOS_KERNEL_AUTH_REQUIRED": "1",
        "AIOS_KERNEL_JWT_SECRET": secret.decode(),
        "AIOS_KERNEL_RATELIMIT_ENABLED": "0",
        "CLOUDTECH_V4_BASE_URL": ct_url,
        "CLOUDTECH_V4_GATEWAY_ENABLED": "1",
        "CLOUDTECH_V4_JWT_SECRET": ct_secret.decode(),
        "CLOUDTECH_V4_REQUIRE_TENANT_JWT": "1",
        "AIOS_SCHEDULER_SQLITE_PATH": str(tmp_path / "durable.db"),
    })
    ct_proc = _start_uvicorn("api.v4.asgi:app", ct_port, cwd=cloudtech, env=ct_env)
    aios_proc = None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await _health_url(client, ct_url + "/v4/workpaths/capabilities", ct_proc)
            aios_proc = _start_uvicorn(
                "aios_kernel.gateway.serve:app", aios_port,
                cwd=aios_root, env=aios_env,
            )
            await _health_url(client, aios_url + "/health", aios_proc)
            task = {
                "goal_id": "cross-repo-end-to-end",
                "title": "CloudTech authorized local-prefix execution",
                "worker": "cloudtech-v4-adapter",
                "input_payload": {
                    "tenant_id": tenant,
                    "path_id": "WP-BLOGGER-RESEARCH",
                    "action": "create_and_execute_local",
                    "input_bindings": {
                        "homepage_url": "https://example.com/creator?q=1",
                        "target_industry": "装修",
                    },
                },
            }
            submitted = await client.post(aios_url + "/tasks", json=task, headers=headers)
            assert submitted.status_code == 202, submitted.text
            run_id = submitted.json()["run_id"]
            response = None
            for _ in range(180):
                response = await client.get(
                    aios_url + f"/tasks/{run_id}/result", headers=headers,
                )
                if response.status_code == 200 and response.json()["available"]:
                    break
                await asyncio.sleep(.08)
            assert response is not None and response.status_code == 200
            data = response.json()
            assert data["state"] == "completed", data
            assert data["business_validated"] is False
            inner = data["artifact"]["inline_json"]["data"]["local_execution"]
            assert inner["executed_nodes"] == ["url_normalize"]
            assert inner["blocked_at"]["reason"] == "MOCK_ONLY"
            assert inner["external_calls"] == 0
            assert inner["charged_cents"] == 0
            forged = sign_jwt(
                {"sub": "other", "tenant_id": "different-tenant"}, secret,
            )
            wrong = await client.get(
                aios_url + f"/tasks/{run_id}/result",
                headers={"Authorization": f"Bearer {forged}"},
            )
            assert wrong.status_code == 404

            # Restart only AIOS. The completed worker Artifact must survive.
            _stop_process(aios_proc)
            aios_proc = _start_uvicorn(
                "aios_kernel.gateway.serve:app", aios_port,
                cwd=aios_root, env=aios_env,
            )
            await _health_url(client, aios_url + "/health", aios_proc)
            restored = await client.get(
                aios_url + f"/tasks/{run_id}/result", headers=headers,
            )
            assert restored.status_code == 200
            assert restored.json()["state"] == "completed"
            assert restored.json()["artifact"] == data["artifact"]

            # Restart CloudTech too: the original V4 Run, nodes and tenant
            # idempotency must survive in CloudTech's own opt-in database.
            cloudtech_run = data["artifact"]["inline_json"]["data"]["created_run"]["run_id"]
            _stop_process(ct_proc)
            ct_proc = _start_uvicorn(
                "api.v4.asgi:app", ct_port, cwd=cloudtech, env=ct_env,
            )
            await _health_url(client, ct_url + "/v4/workpaths/capabilities", ct_proc)
            cloudtech_signed = sign_jwt(
                {"tenant_id": tenant, "user_id": "test-only-inspector"}, ct_secret,
            )
            ct_headers = {"Authorization": f"Bearer {cloudtech_signed}"}
            unauthorized_ct = await client.get(
                ct_url + f"/v4/workpaths/runs/{cloudtech_run}",
                params={"tenant_id": tenant},
            )
            assert unauthorized_ct.status_code == 401
            original = await client.get(
                ct_url + f"/v4/workpaths/runs/{cloudtech_run}",
                params={"tenant_id": tenant}, headers=ct_headers,
            )
            assert original.status_code == 200, original.text
            doc = original.json()
            assert doc["run_id"] == cloudtech_run
            assert doc["status"] == "PARTIAL"
            assert doc["nodes"][0]["node_id"] == "url_normalize"
            assert doc["nodes"][0]["status"] == "COMPLETED"

            reissued = await client.post(
                ct_url + "/v4/workpaths/runs",
                params={"tenant_id": tenant}, headers=ct_headers,
                json={
                    "path_id": "WP-BLOGGER-RESEARCH",
                    "revision": 1,
                    "input_bindings": task["input_payload"]["input_bindings"],
                    "idempotency_key": data["artifact"]["task_id"],
                },
            )
            assert reissued.status_code == 200, reissued.text
            assert reissued.json()["run_id"] == cloudtech_run
    finally:
        if aios_proc is not None:
            _stop_process(aios_proc)
        _stop_process(ct_proc)
