"""P9: AIOS Gateway actually accepts restricted CloudTech task payloads.

No external action or real scheduler process; an instrumented scheduler
verifies the worker binding and exact task envelope submitted.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aios_kernel.gateway.auth import sign_jwt
from aios_kernel.gateway.http import create_app

_TEST_SECRET = b'cross-tenant-gateway-test-secret-1234567890'


def _signed():
    token = sign_jwt({'sub': 'tenant-worker', 'tenant_id': 'tenant-a'}, _TEST_SECRET)
    return {'Authorization': f'Bearer {token}'}


def _post(client, payload):
    return client.post('/tasks', json=payload, headers=_signed())


class _Scheduler:
    def __init__(self):
        self.task = None

    async def submit(self, task, *, priority):
        self.task = task
        return "p9-scheduler-run"

    async def status(self, run_id):
        return {"run_id": run_id, "state": "queued"}

    def metrics(self):
        return {"completed": 0, "submitted": 0}


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "1")
    monkeypatch.setenv("AIOS_KERNEL_JWT_SECRET", _TEST_SECRET.decode())
    monkeypatch.setenv("AIOS_KERNEL_RATELIMIT_ENABLED", "0")
    monkeypatch.setenv("CLOUDTECH_V4_GATEWAY_ENABLED", "1")
    monkeypatch.setenv("CLOUDTECH_V4_BASE_URL", "https://cloudtech.example")
    sched = _Scheduler()
    return TestClient(create_app(sched)), sched


def _request(action="preflight", *, worker="cloudtech-v4-adapter"):
    return {
        "goal_id": "p9-gateway-goal",
        "title": "Inspect existing CloudTech workpath",
        "worker": worker,
        "input_payload": {
            "tenant_id": "tenant-a",
            "path_id": "WP-BLOGGER-RESEARCH",
            "action": action,
        },
    }


def test_gateway_binds_explicit_cloudtech_worker_and_input(setup):
    client, scheduler = setup
    result = _post(client, _request())
    assert result.status_code == 202, result.text
    assert result.json()["run_id"] == "p9-scheduler-run"
    assert scheduler.task.worker == "cloudtech-v4-adapter"
    assert scheduler.task.input_payload["path_id"] == "WP-BLOGGER-RESEARCH"


def test_gateway_forbids_arbitrary_worker_and_publish(setup):
    client, scheduler = setup
    assert _post(client, _request(worker="openclaw-adapter")).status_code == 400
    assert _post(client, _request(action="publish_to_douyin")).status_code == 400
    assert scheduler.task is None


def test_gateway_requires_service_and_opt_in(setup, monkeypatch):
    client, scheduler = setup
    monkeypatch.delenv("CLOUDTECH_V4_BASE_URL")
    assert _post(client, _request()).status_code == 503
    monkeypatch.setenv("CLOUDTECH_V4_BASE_URL", "https://cloudtech.example")
    monkeypatch.setenv("CLOUDTECH_V4_GATEWAY_ENABLED", "0")
    assert _post(client, _request()).status_code == 403
    assert scheduler.task is None


def test_gateway_rejects_unbound_payload_instead_of_executing_random_actions(setup):
    client, scheduler = setup
    request = _request(worker=None)
    assert _post(client, request).status_code == 400
    assert scheduler.task is None


def test_gateway_refuses_cross_tenant_and_unsigned_submission(setup):
    client, scheduler = setup
    unsigned = client.post("/tasks", json=_request())
    assert unsigned.status_code == 401
    wrong = _request()
    wrong["input_payload"]["tenant_id"] = "tenant-b"
    assert _post(client, wrong).status_code == 403
    assert scheduler.task is None


def test_gateway_rejects_cloudtech_if_jwt_auth_is_disabled(monkeypatch):
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "0")
    monkeypatch.setenv("AIOS_KERNEL_RATELIMIT_ENABLED", "0")
    monkeypatch.setenv("CLOUDTECH_V4_GATEWAY_ENABLED", "1")
    monkeypatch.setenv("CLOUDTECH_V4_BASE_URL", "https://cloudtech.example")
    client = TestClient(create_app(_Scheduler()))
    response = client.post("/tasks", json=_request())
    assert response.status_code == 403
