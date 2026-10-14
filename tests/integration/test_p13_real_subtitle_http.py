"""Real P13: JWT-protected AIOS → V4 API → separate durable worker → SRT/VTT.

All servers and the worker are actual OS processes in isolated CI.
The input is user-supplied timed text. NO audio ASR/provider is asserted.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from aios_kernel.gateway.auth import sign_jwt


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _launch(module: str, cwd: Path, port: int, env: dict) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", module,
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(cwd), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )


def _stop(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.communicate(timeout=7)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate(timeout=7)


async def _ready(client: httpx.AsyncClient, endpoint: str, proc: subprocess.Popen):
    for _ in range(160):
        if proc.poll() is not None:
            log = proc.stderr.read() if proc.stderr else ""
            pytest.fail(f"service exited before ready: {log[-2000:]}")
        try:
            response = await client.get(endpoint)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(.1)
    pytest.fail(f"service not ready: {endpoint}")


@pytest.mark.asyncio
async def test_real_subtitle_worker_delivers_source_checked_artifact(tmp_path):
    checkout = os.environ.get("CLOUDTECH_V4_PR2_CHECKOUT")
    if not checkout:
        pytest.skip("real cross-repository PR2 checkout unavailable")
    ct_root = Path(checkout).resolve()
    assert (ct_root / "workflows/v4/local_worker.py").is_file()
    ai_root = Path(__file__).resolve().parents[2]

    tenant = "subtitle-ci-tenant"
    member = "aios-v4-service-worker"
    ct_secret = b"ci-subtitles-cloudtech-tenant-signing-secret-2026"
    ai_secret = b"ci-subtitles-aios-human-signing-secret-2026"

    membership = tmp_path / "members.sqlite3"
    with sqlite3.connect(membership) as db:
        db.execute("CREATE TABLE saas_tenants (tenant_id TEXT PRIMARY KEY, active INTEGER)")
        db.execute("CREATE TABLE saas_users (user_id TEXT, tenant_id TEXT)")
        db.execute("INSERT INTO saas_tenants VALUES (?,1)", (tenant,))
        db.execute("INSERT INTO saas_users VALUES (?,?)", (member, tenant))
        db.commit()

    durable = tmp_path / "cloudtech-v4.sqlite3"
    ct_env = dict(os.environ)
    ct_env.update({
        "PYTHONPATH": str(ct_root),
        "CLOUDTECH_ENV": "staging",
        "V4_ENV": "staging",
        "V4_JWT_SECRET": ct_secret.decode(),
        "CLOUDTECH_SAAS_DB_PATH": str(membership),
        "CLOUDTECH_V4_SQLITE_RUN_STORE": str(durable),
    })
    ct_env.pop("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", None)
    ct_port, ai_port = _port(), _port()
    while ai_port == ct_port:
        ai_port = _port()
    ct_url, ai_url = f"http://127.0.0.1:{ct_port}", f"http://127.0.0.1:{ai_port}"
    ai_env = dict(os.environ)
    ai_env.update({
        "PYTHONPATH": str(ai_root / "src"),
        "AIOS_KERNEL_AUTH_REQUIRED": "1",
        "AIOS_KERNEL_JWT_SECRET": ai_secret.decode(),
        "AIOS_KERNEL_RATELIMIT_ENABLED": "0",
        "CLOUDTECH_V4_BASE_URL": ct_url,
        "CLOUDTECH_V4_GATEWAY_ENABLED": "1",
        "CLOUDTECH_V4_REQUIRE_TENANT_JWT": "1",
        "CLOUDTECH_V4_JWT_SECRET": ct_secret.decode(),
        "AIOS_SCHEDULER_SQLITE_PATH": str(tmp_path / "aios-v4.sqlite3"),
    })
    ai_headers = {
        "Authorization": "Bearer " + sign_jwt(
            {"sub": "user", "tenant_id": tenant}, ai_secret,
        )
    }
    segments = [
        {"start_ms": 0, "end_ms": 1500, "text": "客厅 改造前"},
        {"start_ms": 1800, "end_ms": 3700, "text": "改造后更加通透"},
    ]
    ct_proc = _launch("api.v4.asgi:app", ct_root, ct_port, ct_env)
    ai_proc = None
    worker_proc = None
    try:
        async with httpx.AsyncClient(timeout=7) as client:
            await _ready(client, ct_url + "/v4/workpaths/capabilities", ct_proc)
            p = await client.get(
                ct_url + "/v4/workpaths/WP-LOCAL-SUBTITLE-EXPORT/preflight",
            )
            assert p.status_code == 200
            assert p.json()["local_worker_supported"] is True

            # Real independently running local job consumer; not an in-test fake.
            worker_proc = subprocess.Popen(
                [
                    sys.executable, "-m", "workflows.v4.local_worker",
                    "--loop", "--poll-seconds", "0.2",
                ],
                cwd=ct_root, env=ct_env,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
            ai_proc = _launch("aios_kernel.gateway.serve:app", ai_root, ai_port, ai_env)
            await _ready(client, ai_url + "/health", ai_proc)
            request = {
                "goal_id": "p13-real-user-subtitle",
                "title": "有时间戳的字幕文本生成真正SRT和VTT",
                "worker": "cloudtech-v4-adapter",
                "input_payload": {
                    "action": "create_enqueue_and_collect_subtitles",
                    "tenant_id": tenant,
                    "path_id": "WP-LOCAL-SUBTITLE-EXPORT",
                    "input_bindings": {"segments": segments},
                },
            }
            rejected = await client.post(ai_url + "/tasks", json=request)
            assert rejected.status_code == 401
            accepted = await client.post(
                ai_url + "/tasks", json=request, headers=ai_headers,
            )
            assert accepted.status_code == 202, accepted.text
            run_id = accepted.json()["run_id"]
            evidence = None
            for _ in range(220):
                reply = await client.get(
                    ai_url + f"/tasks/{run_id}/result", headers=ai_headers,
                )
                if reply.status_code == 200 and reply.json().get("available"):
                    evidence = reply.json()
                    break
                await asyncio.sleep(.1)
            assert evidence is not None, "AIOS did not persist a worker receipt"
            assert evidence["state"] == "completed", evidence
            assert evidence["business_validated"] is False
            body = evidence["artifact"]["inline_json"]
            assert body["data"]["source_verified_locally"] is True
            output = body["data"]["local_execution"]["nodes"][0]["output_ref"]
            assert "改造前" in output["srt"] and "改造后" in output["vtt"]
            assert output["mock"] is False
            assert output["asr_performed"] is False
            assert output["model_called"] is False
            assert output["segment_count"] == 2

            ct_run_id = body["data"]["created_run"]["run_id"]
            # Must survive AIOS process restart unchanged.
            _stop(ai_proc)
            ai_proc = _launch("aios_kernel.gateway.serve:app", ai_root, ai_port, ai_env)
            await _ready(client, ai_url + "/health", ai_proc)
            reopened = await client.get(
                ai_url + f"/tasks/{run_id}/result", headers=ai_headers,
            )
            assert reopened.status_code == 200
            assert reopened.json()["artifact"] == evidence["artifact"]

            # CloudTech status persists independently from its worker.
            _stop(ct_proc)
            ct_proc = _launch("api.v4.asgi:app", ct_root, ct_port, ct_env)
            await _ready(client, ct_url + "/v4/workpaths/capabilities", ct_proc)
            ct_headers = {
                "Authorization": "Bearer " + sign_jwt(
                    {"user_id": member, "tenant_id": tenant}, ct_secret,
                )
            }
            final = await client.get(
                ct_url + f"/v4/workpaths/runs/{ct_run_id}",
                params={"tenant_id": tenant}, headers=ct_headers,
            )
            assert final.status_code == 200, final.text
            assert final.json()["status"] == "COMPLETED"
            assert final.json()["nodes"][0]["output_ref"]["srt"] == output["srt"]
    finally:
        _stop(worker_proc)
        _stop(ai_proc)
        _stop(ct_proc)
