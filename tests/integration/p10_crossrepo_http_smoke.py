"""P10 GitHub Actions real loopback HTTP smoke: AIOS -> CloudTech V4.

Two live ASGI processes, two existing repos, actual SQLite task journal.
No real social network, paid API, Windows deployment, or fake content success.
"""
from __future__ import annotations

import os
import time

import httpx

from aios_kernel.gateway.auth import sign_jwt

AIOS = "http://127.0.0.1:5090"
CT = "http://127.0.0.1:5089"
SECRET = os.environ["AIOS_KERNEL_JWT_SECRET"].encode()
TENANT = "isolated-ci-tenant"


def _jwt(tenant: str) -> dict[str, str]:
    token = sign_jwt({"sub": "p10-smoke", "tenant_id": tenant}, SECRET)
    return {"Authorization": f"Bearer {token}"}


def wait_ready(client: httpx.Client, url: str) -> None:
    last = ""
    for _ in range(100):
        try:
            response = client.get(url, timeout=1)
            if response.status_code == 200:
                return
            last = f"{response.status_code}: {response.text[:180]}"
        except httpx.HTTPError as exc:
            last = type(exc).__name__
        time.sleep(0.2)
    raise AssertionError(f"ASGI service not ready: {url}, last={last}")


def run() -> None:
    with httpx.Client(timeout=25.0) as client:
        wait_ready(client, f"{CT}/v4/workpaths/capabilities")
        wait_ready(client, f"{AIOS}/health")
        caps = client.get(f"{CT}/v4/workpaths/capabilities").json()
        assert caps["total_paths"] == 6, caps
        assert caps["execution_ready_paths"] == 0, caps

        payload = {
            "goal_id": "p10-real-http",
            "title": "Execute existing CloudTech V4 local-only prefix",
            "worker": "cloudtech-v4-adapter",
            "input_payload": {
                "action": "create_and_execute_local",
                "tenant_id": TENANT,
                "path_id": "WP-BLOGGER-RESEARCH",
                "input_bindings": {
                    "homepage_url": "https://example.com/creator?cursor=1",
                    "target_industry": "renovation",
                },
            },
        }
        no_jwt = client.post(f"{AIOS}/tasks", json=payload)
        assert no_jwt.status_code == 401, no_jwt.text
        wrong = client.post(f"{AIOS}/tasks", json=payload, headers=_jwt("wrong"))
        assert wrong.status_code == 403, wrong.text

        created = client.post(f"{AIOS}/tasks", json=payload, headers=_jwt(TENANT))
        assert created.status_code == 202, created.text
        run_id = created.json()["run_id"]
        state = None
        for _ in range(200):
            response = client.get(f"{AIOS}/tasks/{run_id}", headers=_jwt(TENANT))
            assert response.status_code == 200, response.text
            state = response.json()["state"]
            if state in {"completed", "failed", "blocked_uncertain"}:
                break
            time.sleep(0.1)
        assert state == "completed", f"expected completed worker, got {state}"

        outside = client.get(
            f"{AIOS}/tasks/{run_id}/result", headers=_jwt("wrong")
        )
        assert outside.status_code == 404, outside.text
        result = client.get(
            f"{AIOS}/tasks/{run_id}/result", headers=_jwt(TENANT)
        )
        assert result.status_code == 200, result.text
        doc = result.json()
        assert doc["available"] is True, doc
        assert doc["business_validated"] is False, doc
        artifact = doc["artifact"]["inline_json"]
        assert artifact["provider_call_allowed"] is False
        remote = artifact["data"]["local_execution"]
        assert remote["executed_nodes"] == ["url_normalize"], remote
        assert remote["blocked_at"]["operation"] == "platform.permission_check"
        assert remote["external_calls"] == 0
        assert remote["charged_cents"] == 0
        print("P10 REAL-HTTP PASS: two ASGI servers, six source paths, safe first node,")
        print("  tenant authorization, persisted run, no external effects, artifact proof")
        print("  NOTE: Windows deployment / actual media provider / business validation: NOT TESTED")


if __name__ == "__main__":
    run()
