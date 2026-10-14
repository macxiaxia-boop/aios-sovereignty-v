"""P14: actual AIOS -> CloudTech independent article worker -> verified outbox.

Only user-supplied HTML is handled. No third-party scraping, LLM, ASR, paid
provider, production tenancy or automated publishing is claimed.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from aios_kernel.gateway.auth import sign_jwt
from tests.integration.test_p13_real_subtitle_http import _launch, _port, _ready, _stop


@pytest.mark.asyncio
async def test_two_services_worker_outbox_and_restart_preserve_real_article(tmp_path):
    checkout = os.environ.get("CLOUDTECH_V4_PR2_CHECKOUT")
    if not checkout:
        pytest.skip("real CloudTech PR2 checkout required, no mock substitute")
    ct_root = Path(checkout).resolve()
    assert (ct_root / "workflows/v4/local_worker.py").is_file()
    ai_root = Path(__file__).resolve().parents[2]

    tenant, member = "article-analysis-ci", "aios-v4-service-worker"
    ct_secret = b"ci-only-cloudtech-article-analysis-2026-012345"
    ai_secret = b"ci-only-aios-article-analysis-human-2026-012345"
    membership = tmp_path / "members.sqlite3"
    with sqlite3.connect(membership) as db:
        db.execute("CREATE TABLE saas_tenants (tenant_id TEXT PRIMARY KEY, active INTEGER)")
        db.execute("CREATE TABLE saas_users (user_id TEXT, tenant_id TEXT)")
        db.execute("INSERT INTO saas_tenants VALUES (?,1)", (tenant,))
        db.execute("INSERT INTO saas_users VALUES (?,?)", (member, tenant))

    ct_env = dict(os.environ)
    ct_env.update({
        "PYTHONPATH": str(ct_root),
        "CLOUDTECH_ENV": "staging",
        "V4_ENV": "staging",
        "V4_JWT_SECRET": ct_secret.decode(),
        "CLOUDTECH_SAAS_DB_PATH": str(membership),
        "CLOUDTECH_V4_SQLITE_RUN_STORE": str(tmp_path / "ct.sqlite3"),
    })
    ct_env.pop("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", None)
    ct_port, ai_port = _port(), _port()
    while ai_port == ct_port:
        ai_port = _port()
    ct_url = f"http://127.0.0.1:{ct_port}"
    ai_url = f"http://127.0.0.1:{ai_port}"
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
        "AIOS_SCHEDULER_SQLITE_PATH": str(tmp_path / "ai.sqlite3"),
    })
    token = sign_jwt({"sub": "human-owner", "tenant_id": tenant}, ai_secret)
    headers = {"Authorization": "Bearer " + token}
    html = (
        "<!doctype html><html><head><title>客厅方案</title></head>"
        "<body><article><h1>二手房客厅改造</h1>"
        "<p>如何保留原结构并控制成本？</p>"
        "<p>先确认实际尺寸，再规划预算。</p>"
        "<p>关注后续案例。</p>"
        '<img src="/rooms/before.jpg" alt="改造前">'
        "</article></body></html>"
    )
    expected_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    ct_proc = _launch("api.v4.asgi:app", ct_root, ct_port, ct_env)
    worker = None
    ai_proc = None
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await _ready(client, ct_url + "/v4/workpaths/capabilities", ct_proc)
            worker = subprocess.Popen(
                [sys.executable, "-m", "workflows.v4.local_worker",
                 "--loop", "--poll-seconds", "0.2"],
                cwd=ct_root, env=ct_env,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
            ai_proc = _launch("aios_kernel.gateway.serve:app", ai_root, ai_port, ai_env)
            await _ready(client, ai_url + "/health", ai_proc)
            request = {
                "goal_id": "real-local-article-analysis",
                "title": "实际文章正文配图及结构分析",
                "worker": "cloudtech-v4-adapter",
                "input_payload": {
                    "tenant_id": tenant,
                    "action": "create_enqueue_and_collect_article_analysis",
                    "path_id": "WP-LOCAL-ARTICLE-ANALYZE",
                    "input_bindings": {
                        "html": html,
                        "source_url": "https://example.org/rooms/article",
                    },
                },
            }
            assert (await client.post(ai_url + "/tasks", json=request)).status_code == 401
            submitted = await client.post(
                ai_url + "/tasks", json=request, headers=headers,
            )
            assert submitted.status_code == 202, submitted.text
            run_id = submitted.json()["run_id"]
            response = None
            for _ in range(200):
                result = await client.get(
                    ai_url + f"/tasks/{run_id}/result", headers=headers,
                )
                if result.status_code == 200 and result.json().get("available"):
                    response = result.json()
                    break
                await asyncio.sleep(0.1)
            assert response is not None and response["state"] == "completed"
            assert response["business_validated"] is False
            doc = response["artifact"]["inline_json"]
            assert doc["data"]["source_verified_locally"] is True
            assert doc["data"]["storage"] == "SQLITE_LOCAL_DURABLE"
            nodes = doc["data"]["local_execution"]["nodes"]
            assert [n["node_id"] for n in nodes] == ["html_parse", "content_analyze"]
            original, analysis = nodes[0]["output_ref"], nodes[1]["output_ref"]
            assert original["content_sha256"] == expected_sha
            assert original["mock"] is False
            assert "保留原结构" in original["text"]
            assert len(original["images"]) == 1
            assert original["images"][0]["url"] == "https://example.org/rooms/before.jpg"
            assert analysis["source_html_sha256"] == expected_sha
            assert analysis["text_sha256"] == hashlib.sha256(
                original["text"].encode("utf-8")
            ).hexdigest()
            assert analysis["analysis_method"] == "deterministic_lexical_counts_v1"
            assert analysis["ai_model_used"] is False
            assert any("关注" in item["matched_terms"]
                       for item in analysis["cta_term_matches"])
            proof = doc["data"]["verified_catalog_entry"]
            assert proof["run_id"] == doc["data"]["created_run"]["run_id"]
            assert proof["artifact_kind"] == "ARTICLE_CONTENT_ANALYSIS"
            assert proof["source_sha256"] == expected_sha
            assert proof["output_sha256"] == doc["data"]["output_sha256"]
            assert doc["data"]["local_execution"]["budget_spent_cents"] == 0

            other = sign_jwt({"sub": "other", "tenant_id": "another-tenant"}, ai_secret)
            denied = await client.get(
                ai_url + f"/tasks/{run_id}/result",
                headers={"Authorization": "Bearer " + other},
            )
            assert denied.status_code == 404

            _stop(ai_proc)
            ai_proc = _launch("aios_kernel.gateway.serve:app", ai_root, ai_port, ai_env)
            await _ready(client, ai_url + "/health", ai_proc)
            restored = await client.get(
                ai_url + f"/tasks/{run_id}/result", headers=headers,
            )
            assert restored.status_code == 200
            assert restored.json()["artifact"] == response["artifact"]

            _stop(ct_proc)
            ct_proc = _launch("api.v4.asgi:app", ct_root, ct_port, ct_env)
            await _ready(client, ct_url + "/v4/workpaths/capabilities", ct_proc)
            service_jwt = sign_jwt(
                {"user_id": member, "tenant_id": tenant}, ct_secret
            )
            remote_headers = {"Authorization": "Bearer " + service_jwt}
            catalog = await client.get(
                ct_url + "/v4/workpaths/local-outputs",
                params={"tenant_id": tenant}, headers=remote_headers,
            )
            assert catalog.status_code == 200, catalog.text
            entries = [x for x in catalog.json()["items"]
                       if x["run_id"] == proof["run_id"]]
            assert len(entries) == 1
            assert entries[0]["output_sha256"] == proof["output_sha256"]
            assert catalog.json()["raw_customer_content_in_response"] is False
    finally:
        _stop(worker)
        _stop(ai_proc)
        _stop(ct_proc)
