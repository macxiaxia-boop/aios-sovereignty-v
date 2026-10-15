"""P12: live-contract shape tests for CloudTech PR2 real user-supplied HTML.

No web fetching, model/API charge or publishing. Outputs remain NOT business
validated even when local source-hash reconciliation passes.
"""
from __future__ import annotations

import hashlib

import httpx
import pytest

from aios_kernel.domain.task import Task
from aios_kernel.workers.cloudtech_v4_adapter import CloudTechV4Adapter


def _task():
    return Task(
        goal_id="safe-local-article",
        title="Parse supplied article HTML",
        worker="cloudtech-v4-adapter",
        input_payload={
            "tenant_id": "tenant-a",
            "action": "create_and_execute_local",
            "path_id": "WP-LOCAL-ARTICLE-EXTRACT",
            "input_bindings": {
                "html": "<html><title>真实标题</title><article>真实正文</article></html>",
                "source_url": "https://example.com/my-article",
            },
        },
    )


def _transport(task: Task, *, wrong_digest: bool):
    html = task.input_payload["input_bindings"]["html"]
    digest = hashlib.sha256(html.encode()).hexdigest()
    if wrong_digest:
        digest = "0" * 64

    def handle(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/preflight"):
            return httpx.Response(200, json={
                "path_id": "WP-LOCAL-ARTICLE-EXTRACT",
                "revision": 1,
                "level": "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION",
                "execution_ready": False,
            })
        if req.url.path == "/v4/workpaths/runs":
            return httpx.Response(200, json={"run_id": "wpr_article0001"})
        if req.url.path.endswith("/execute-local"):
            return httpx.Response(200, json={
                "run_id": "wpr_article0001",
                "status": "COMPLETED",
                "worker_type": "SYNCHRONOUS_LOCAL_ONLY",
                "provider_called": False, "cost_cents": 0,
                "storage": "SQLITE_LOCAL_DURABLE",
                "nodes": [{
                    "node_id": "html_parse", "operation": "article.html_parse",
                    "status": "COMPLETED", "cost_cents": 0,
                    "input_hash": digest,
                    "output_ref": {
                        "title": "真实标题", "text": "真实正文",
                        "mock": False, "retrieval_policy": "supplied_html_only",
                        "content_sha256": digest,
                    },
                }],
            })
        return httpx.Response(404)

    return httpx.MockTransport(handle)


@pytest.mark.asyncio
async def test_real_local_html_contract_produces_sha_bound_artifact(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_V4_JWT_SECRET", raising=False)
    monkeypatch.delenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", raising=False)
    task = _task()
    async with httpx.AsyncClient(
        transport=_transport(task, wrong_digest=False),
    ) as client:
        adapter = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        artifact = await adapter.execute(task)
    assert artifact.inline_json["business_validated"] is False
    assert artifact.inline_json["data"]["source_verified_locally"] is True
    assert artifact.inline_json["data"]["storage"] == "SQLITE_LOCAL_DURABLE"
    assert len(artifact.inline_json["data"]["output_sha256"]) == 64


@pytest.mark.asyncio
async def test_forged_html_digest_fails_closed(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_V4_JWT_SECRET", raising=False)
    monkeypatch.delenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", raising=False)
    task = _task()
    async with httpx.AsyncClient(
        transport=_transport(task, wrong_digest=True),
    ) as client:
        adapter = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        with pytest.raises(ValueError, match="source provenance"):
            await adapter.execute(task)
