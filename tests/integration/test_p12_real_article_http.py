"""Real two-process AIOS → CloudTech PR2 user-supplied HTML extraction.

This uses actual ASGI servers and two local SQLite databases, not MockTransport.
It does not fetch a third-party URL, incur model costs, or publish content.
Production membership is verified against a test-only SaaS identity database.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from aios_kernel.gateway.auth import sign_jwt


def _unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _launch(module: str, path: Path, port: int, env: dict) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", module,
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(path), env=env, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE, text=True,
    )


def _stop(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.communicate(timeout=7)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=7)


async def _ready(client: httpx.AsyncClient, endpoint: str, proc: subprocess.Popen):
    for _ in range(180):
        if proc.poll() is not None:
            message = proc.stderr.read() if proc.stderr else ""
            pytest.fail(f"actual ASGI service crashed: {message[-2000:]}")
        try:
            r = await client.get(endpoint)
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(.1)
    pytest.fail(f"actual ASGI endpoint not ready: {endpoint}")


@pytest.mark.asyncio
async def test_two_real_hosts_process_and_restore_supplied_html(tmp_path):
    checkout = os.environ.get("CLOUDTECH_V4_PR2_CHECKOUT")
    if not checkout:
        pytest.skip("external CloudTech PR2 checkout required; not a unit-test mock")
    cloudtech = Path(checkout).resolve()
    assert (cloudtech / "api/v4/asgi.py").is_file()

    ai_root = Path(__file__).resolve().parents[2]
    ct_port = _unused_port()
    ai_port = _unused_port()
    while ai_port == ct_port:
        ai_port = _unused_port()
    ct_url = f"http://127.0.0.1:{ct_port}"
    ai_url = f"http://127.0.0.1:{ai_port}"

    tenant, member = "article-tenant", "aios-v4-service-worker"
    ct_secret = b"test-only-cloudtech-html-service-identity-123456"
    ai_secret = b"test-only-aios-user-identity-123456789012345"
    member_db = tmp_path / "members.db"
    with sqlite3.connect(member_db) as db:
        db.execute("CREATE TABLE saas_tenants (tenant_id TEXT PRIMARY KEY, active INTEGER)")
        db.execute("CREATE TABLE saas_users (user_id TEXT, tenant_id TEXT)")
        db.execute("INSERT INTO saas_tenants VALUES (?, 1)", (tenant,))
        db.execute("INSERT INTO saas_users VALUES (?, ?)", (member, tenant))
        db.commit()

    ct_env = dict(os.environ)
    ct_env.update({
        "PYTHONPATH": str(cloudtech),
        "CLOUDTECH_ENV": "production",
        "V4_ENV": "production",
        "V4_JWT_SECRET": ct_secret.decode(),
        "CLOUDTECH_SAAS_DB_PATH": str(member_db),
        "CLOUDTECH_V4_SQLITE_RUN_STORE": str(tmp_path / "cloudtech-runs.sqlite3"),
    })
    ct_env.pop("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", None)
    ai_env = dict(os.environ)
    ai_env.update({
        "PYTHONPATH": str(ai_root / "src"),
        "AIOS_KERNEL_AUTH_REQUIRED": "1",
        "AIOS_KERNEL_JWT_SECRET": ai_secret.decode(),
        "AIOS_KERNEL_RATELIMIT_ENABLED": "0",
        "CLOUDTECH_V4_GATEWAY_ENABLED": "1",
        "CLOUDTECH_V4_BASE_URL": ct_url,
        "CLOUDTECH_V4_REQUIRE_TENANT_JWT": "1",
        "CLOUDTECH_V4_JWT_SECRET": ct_secret.decode(),
        "AIOS_SCHEDULER_SQLITE_PATH": str(tmp_path / "aios-runs.sqlite3"),
    })
    ai_headers = {
        "Authorization": f"Bearer {sign_jwt({'sub': 'human-operator', 'tenant_id': tenant}, ai_secret)}"
    }
    html = (
        "<!doctype html><html><head><title>真实装修文章</title></head>"
        "<body><article><h1>二手房改造</h1><p>保留结构，合理利用空间。</p>"
        "</article></body></html>"
    )
    digest = hashlib.sha256(html.encode()).hexdigest()
    cloudtech_proc = _launch("api.v4.asgi:app", cloudtech, ct_port, ct_env)
    aios_proc = None
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await _ready(
                client, ct_url + "/v4/workpaths/capabilities", cloudtech_proc,
            )
            preflight = (await client.get(
                ct_url + "/v4/workpaths/WP-LOCAL-ARTICLE-EXTRACT/preflight",
            )).json()
            assert preflight["local_sync_supported"] is True
            assert preflight["business_validated"] is False

            aios_proc = _launch(
                "aios_kernel.gateway.serve:app", ai_root, ai_port, ai_env,
            )
            await _ready(client, ai_url + "/health", aios_proc)
            payload = {
                "goal_id": "real-owned-html",
                "title": "真实用户提供 HTML 的无网络正文提取",
                "worker": "cloudtech-v4-adapter",
                "input_payload": {
                    "tenant_id": tenant,
                    "path_id": "WP-LOCAL-ARTICLE-EXTRACT",
                    "action": "create_and_execute_local",
                    "input_bindings": {
                        "html": html,
                        "source_url": "https://example.com/user-owned-article",
                    },
                },
            }
            unauthorized = await client.post(ai_url + "/tasks", json=payload)
            assert unauthorized.status_code == 401
            created = await client.post(
                ai_url + "/tasks", json=payload, headers=ai_headers,
            )
            assert created.status_code == 202, created.text
            run_id = created.json()["run_id"]
            result = None
            for _ in range(180):
                response = await client.get(
                    ai_url + f"/tasks/{run_id}/result", headers=ai_headers,
                )
                if response.status_code == 200 and response.json().get("available"):
                    result = response.json()
                    break
                await asyncio.sleep(.1)
            assert result is not None and result["state"] == "completed"
            assert result["business_validated"] is False
            artifact = result["artifact"]["inline_json"]
            assert artifact["data"]["source_verified_locally"] is True
            assert artifact["data"]["storage"] == "SQLITE_LOCAL_DURABLE"
            node = artifact["data"]["local_execution"]["nodes"][0]
            assert node["input_hash"] == digest
            extracted = node["output_ref"]
            assert extracted["mock"] is False
            assert extracted["content_sha256"] == digest
            assert "保留结构" in extracted["text"]
            assert extracted["title"] == "真实装修文章"
            assert artifact["data"]["local_execution"]["cost_cents"] == 0

            wrong = sign_jwt(
                {"sub": "other-user", "tenant_id": "different"}, ai_secret,
            )
            not_owned = await client.get(
                ai_url + f"/tasks/{run_id}/result",
                headers={"Authorization": f"Bearer {wrong}"},
            )
            assert not_owned.status_code == 404

            ct_run_id = artifact["data"]["created_run"]["run_id"]
            _stop_process(aios_proc)
            aios_proc = _launch(
                "aios_kernel.gateway.serve:app", ai_root, ai_port, ai_env,
            )
            await _ready(client, ai_url + "/health", aios_proc)
            revived = await client.get(
                ai_url + f"/tasks/{run_id}/result", headers=ai_headers,
            )
            assert revived.status_code == 200
            assert revived.json()["artifact"] == result["artifact"]

            _stop_process(cloudtech_proc)
            cloudtech_proc = _launch(
                "api.v4.asgi:app", cloudtech, ct_port, ct_env,
            )
            await _ready(client, ct_url + "/v4/workpaths/capabilities", cloudtech_proc)
            ct_auth = {
                "Authorization": f"Bearer {sign_jwt({'user_id': member, 'tenant_id': tenant}, ct_secret)}"
            }
            restored = await client.get(
                ct_url + f"/v4/workpaths/runs/{ct_run_id}",
                params={"tenant_id": tenant}, headers=ct_auth,
            )
            assert restored.status_code == 200, restored.text
            assert restored.json()["nodes"][0]["input_hash"] == digest
            assert restored.json()["status"] == "COMPLETED"
    finally:
        if aios_proc is not None:
            _stop_process(aios_proc)
        _stop_process(cloudtech_proc)
