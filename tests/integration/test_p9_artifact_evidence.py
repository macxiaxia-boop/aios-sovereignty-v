"""P9 real in-process Artifact result and JWT-protected read surface."""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from aios_kernel.domain.task import Task
from aios_kernel.gateway.auth import sign_jwt
from aios_kernel.gateway.http import create_app
from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig
from aios_kernel.workers.base import _StubAdapterBase
from aios_kernel.workers.registry import WorkerRegistry


@pytest.mark.asyncio
async def test_scheduler_retains_worker_artifact_separately_from_business_success():
    registry = WorkerRegistry()
    registry.register(_StubAdapterBase("codex-adapter"))
    scheduler = AIOSScheduler(
        registry=registry, config=SchedulerConfig(max_concurrent=1)
    )
    await scheduler.start()
    try:
        rid = await scheduler.submit(Task(
            goal_id="p9-proof-goal", title="isolated artifact",
            input_payload={"tenant_id": "owner-only"},
        ))
        for _ in range(100):
            if (await scheduler.status(rid))["state"] == "completed":
                break
            await asyncio.sleep(0.01)
        result = await scheduler.result(rid, tenant_id="owner-only")
        assert result["available"] is True
        assert result["business_validated"] is False
        assert result["artifact"]["task_id"]
        assert result["artifact"]["inline_json"]["worker"] == "codex-adapter"
        blocked = await scheduler.result(rid, tenant_id="wrong-tenant")
        assert blocked["state"] == "unknown"
        assert blocked["available"] is False
    finally:
        await scheduler.stop()


class _ResultScheduler:
    def metrics(self):
        return {}

    async def result(self, run_id, *, tenant_id=None):
        if tenant_id != "owner":
            return {"run_id": run_id, "state": "unknown", "available": False}
        return {
            "run_id": run_id, "state": "completed", "available": True,
            "artifact": {"inline_json": {"path": "example"}},
            "business_validated": False,
        }


def test_gateway_requires_signed_tenant_claim_for_artifact_read(monkeypatch):
    secret = b"p9-artifact-secret-with-32-plus-bytes"
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "1")
    monkeypatch.setenv("AIOS_KERNEL_JWT_SECRET", secret.decode())
    monkeypatch.setenv("AIOS_KERNEL_RATELIMIT_ENABLED", "0")
    app = create_app(_ResultScheduler())

    with TestClient(app) as client:
        unauth = client.get("/tasks/example/result")
        assert unauth.status_code == 401
        no_tenant = sign_jwt({"sub": "tester"}, secret)
        assert client.get(
            "/tasks/example/result",
            headers={"Authorization": f"Bearer {no_tenant}"},
        ).status_code == 403
        owner = sign_jwt({"sub": "tester", "tenant_id": "owner"}, secret)
        valid = client.get(
            "/tasks/example/result",
            headers={"Authorization": f"Bearer {owner}"},
        )
        assert valid.status_code == 200
        assert valid.json()["business_validated"] is False
        status_ok = client.get(
            "/tasks/example",
            headers={"Authorization": f"Bearer {owner}"},
        )
        assert status_ok.status_code == 200
        assert status_ok.json()["state"] == "completed"
        outsider = sign_jwt({"sub": "other", "tenant_id": "outsider"}, secret)
        invalid = client.get(
            "/tasks/example/result",
            headers={"Authorization": f"Bearer {outsider}"},
        )
        assert invalid.status_code == 404
        other_status = client.get(
            "/tasks/example",
            headers={"Authorization": f"Bearer {outsider}"},
        )
        assert other_status.status_code == 404
