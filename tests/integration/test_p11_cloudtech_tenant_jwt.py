"""P11 cross-service tenant-token handshake, with no real credentials.

The CloudTech V4 server accepts only a signed HS256 tenant JWT when configured
with V4_JWT_SECRET. The AIOS bridge signs each tenant separately.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest

from aios_kernel.domain.task import Task
from aios_kernel.workers.cloudtech_v4_adapter import CloudTechV4Adapter


_TEST_SECRET = "this-is-an-ephemeral-test-only-shared-secret-2026"


def _decode_verified(token: str) -> dict:
    head, payload, signature = token.split(".")
    assert json.loads(base64.urlsafe_b64decode(head + "=" * (-len(head) % 4))) == {
        "alg": "HS256", "typ": "JWT",
    }
    expected = hmac.new(
        _TEST_SECRET.encode(), f"{head}.{payload}".encode(), hashlib.sha256,
    ).digest()
    assert hmac.compare_digest(
        expected, base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)),
    )
    result = json.loads(base64.urlsafe_b64decode(
        payload + "=" * (-len(payload) % 4),
    ))
    assert result["iat"] <= time.time() <= result["exp"]
    assert result["exp"] - result["iat"] <= 120
    return result


@pytest.mark.asyncio
async def test_bridge_signs_distinct_tenant_identity_per_operation(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_V4_JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", "1")
    sent = []

    def fake_server(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/preflight"):
            return httpx.Response(200, json={
                "path_id": "WP-BLOGGER-RESEARCH", "revision": 1,
                "level": "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION",
                "execution_ready": False,
            })
        header = req.headers["authorization"]
        assert header.startswith("Bearer ")
        claims = _decode_verified(header[7:])
        assert req.url.params["tenant_id"] == claims["tenant_id"]
        assert claims["permissions"] == ["v4:local-only"]
        sent.append((req.url.path, claims["tenant_id"], header))
        if req.url.path.endswith("/execute-local"):
            return httpx.Response(200, json={
                "run_id": "wpr_test123", "executed_nodes": ["url_normalize"],
                "external_calls": 0, "charged_cents": 0,
                "durability": "IN_PROCESS_ONLY_NOT_PRODUCTION_DURABLE",
                "blocked_at": {"reason": "MOCK_ONLY"},
            })
        return httpx.Response(200, json={"run_id": "wpr_test123"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(fake_server),
    ) as client:
        adapter = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        for tenant in ["alpha", "beta"]:
            task = Task(
                goal_id="g", title="local only", worker=adapter.worker_id,
                input_payload={
                    "action": "create_and_execute_local",
                    "tenant_id": tenant,
                    "path_id": "WP-BLOGGER-RESEARCH",
                    "input_bindings": {"homepage_url": "https://example.com/u"},
                },
            )
            result = await adapter.execute(task)
            assert result.inline_json["tenant_id"] == tenant
            assert result.inline_json["business_validated"] is False

    assert len(sent) == 4
    assert [s[1] for s in sent] == ["alpha", "alpha", "beta", "beta"]
    assert sent[0][2] != sent[2][2]


def test_required_mode_rejects_missing_or_weak_cross_service_secret(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", "1")
    monkeypatch.delenv("CLOUDTECH_V4_JWT_SECRET", raising=False)
    with pytest.raises(ValueError, match="requires a signing secret"):
        CloudTechV4Adapter(base_url="https://cloudtech.example")
    monkeypatch.setenv("CLOUDTECH_V4_JWT_SECRET", "short")
    with pytest.raises(ValueError, match="at least 32"):
        CloudTechV4Adapter(base_url="https://cloudtech.example")
