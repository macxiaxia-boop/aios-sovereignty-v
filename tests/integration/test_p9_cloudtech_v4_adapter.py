"""AIOS ↔ CloudTech V4 protocol tests, using mock HTTP transport.

No actual CloudTech service, credentials, charge, publication or Windows
deployment is involved. Assert identity + side-effect boundary on every call.
"""
from __future__ import annotations

import json

import httpx
import pytest

from aios_kernel.domain.task import Task
from aios_kernel.workers.cloudtech_v4_adapter import CloudTechV4Adapter
from aios_kernel.workers.registry import WorkerRegistry


def _task(action="create_and_execute_local"):
    return Task(
        goal_id="p9-goal", title="CloudTech source-level verification",
        worker="cloudtech-v4-adapter",
        input_payload={
            "action": action, "tenant_id": "tenant-v4",
            "path_id": "WP-BLOGGER-RESEARCH",
            "input_bindings": {"homepage_url": "https://example.com/creator"},
        },
    )


def _preflight():
    return {
        "path_id": "WP-BLOGGER-RESEARCH",
        "revision": 1,
        "level": "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION",
        "execution_ready": False,
        "nodes": [{"id": "url_normalize", "capability": "LOCAL_IMPLEMENTED"}],
    }


@pytest.mark.asyncio
async def test_readonly_preflight_emits_artifact_with_actual_hash():
    calls = []

    def transport(request):
        calls.append((request.method, request.url.path))
        return httpx.Response(200, json=_preflight())

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        worker = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        registry = WorkerRegistry()
        registry.register(worker)
        task = _task("preflight")
        assert registry.route(task) is worker
        artifact = await worker.execute(task)

    assert calls == [("GET", "/v4/workpaths/WP-BLOGGER-RESEARCH/preflight")]
    assert artifact.inline_json["business_validated"] is False
    assert artifact.inline_json["provider_call_allowed"] is False
    assert artifact.task_id == str(task.id)
    assert artifact.has_payload is True
    assert len(artifact.hash_sha256) == 64


@pytest.mark.asyncio
async def test_local_flow_calls_cloudtech_three_times_without_external_effects():
    calls = []
    task = _task()

    def transport(request):
        calls.append((request.method, request.url.path, request.url.params))
        if request.url.path.endswith("/preflight"):
            return httpx.Response(200, json=_preflight())
        if request.url.path == "/v4/workpaths/runs":
            doc = json.loads(request.content.decode())
            assert doc["idempotency_key"] == str(task.id)
            assert request.url.params["tenant_id"] == "tenant-v4"
            return httpx.Response(200, json={"run_id": "wpr_12345678", "status": "READY"})
        assert request.url.path.endswith("/execute-local")
        assert request.url.params["tenant_id"] == "tenant-v4"
        return httpx.Response(200, json={
            "run_id": "wpr_12345678", "executed_nodes": ["url_normalize"],
            "blocked_at": {"operation": "platform.permission_check", "reason": "MOCK_ONLY"},
            "status": "PARTIAL", "external_calls": 0, "charged_cents": 0,
            "durability": "IN_PROCESS_ONLY_NOT_PRODUCTION_DURABLE",
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        worker = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        artifact = await worker.execute(task)
    assert [name for name, _path, _params in calls] == ["GET", "POST", "POST"]
    assert artifact.inline_json["data"]["local_execution"]["status"] == "PARTIAL"
    assert artifact.inline_json["business_validated"] is False
    assert artifact.inline_json["provider_call_allowed"] is False


@pytest.mark.asyncio
async def test_remote_adapter_rejects_false_no_side_effect_attestation():
    task = _task()

    def transport(request):
        if request.url.path.endswith("/preflight"):
            return httpx.Response(200, json=_preflight())
        if request.url.path == "/v4/workpaths/runs":
            return httpx.Response(200, json={"run_id": "wpr_12345678"})
        return httpx.Response(200, json={
            "run_id": "wpr_12345678",
            "external_calls": 1, "charged_cents": 100,
            "durability": "IN_PROCESS_ONLY_NOT_PRODUCTION_DURABLE",
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        worker = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        with pytest.raises(ValueError, match="zero-side-effect contract"):
            await worker.execute(task)


@pytest.mark.asyncio
async def test_unapproved_cloudtech_action_is_rejected_without_any_network():
    def transport(request):
        raise AssertionError("unauthorized action must not reach network")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        worker = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        with pytest.raises(ValueError, match="only allows"):
            await worker.execute(_task("publish_to_social_media"))


def test_cloudtech_worker_requires_explicit_service_url(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_V4_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="explicitly configured"):
        CloudTechV4Adapter()
