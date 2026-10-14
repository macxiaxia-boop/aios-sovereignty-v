"""P9 lifecycle test of the real AIOS Gateway + Scheduler (stub worker only).

Runs solely in TestClient lifespan; does not contact Codex, CloudTech,
Windows tools, paid models, or any external service.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from aios_kernel.workers.base import _StubAdapterBase
from aios_kernel.workers.registry import WorkerRegistry


def test_hosted_gateway_submits_and_tracks_real_scheduler_task(monkeypatch):
    import aios_kernel.gateway.serve as host

    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "0")
    monkeypatch.setenv("AIOS_KERNEL_RATELIMIT_ENABLED", "0")

    def fake_registry():
        registry = WorkerRegistry()
        registry.register(_StubAdapterBase("codex-adapter"))
        return registry

    monkeypatch.setattr(host, "build_default_registry", fake_registry)
    app = host.create_hosted_app()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        submit = client.post(
            "/tasks", json={"goal_id": "p9-host", "title": "isolated task"},
        )
        assert submit.status_code == 202
        run_id = submit.json()["run_id"]

        last = None
        for _ in range(50):
            response = client.get(f"/tasks/{run_id}")
            assert response.status_code == 200
            last = response.json()["state"]
            if last in {"completed", "failed"}:
                break
            time.sleep(0.01)
        assert last == "completed"
