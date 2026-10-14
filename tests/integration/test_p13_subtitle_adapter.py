"""P13: AIOS collects real CloudTech-style durable subtitle job receipts.

Mocked transport isolates logic; a separate CI starts a real local worker.
No ASR is claimed, no network provider is contacted, no paid usage.
"""
from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from aios_kernel.domain.task import Task
from aios_kernel.workers.cloudtech_v4_adapter import CloudTechV4Adapter


SEGMENTS = [
    {"start_ms": 0, "end_ms": 1500, "text": "改造前空间狭小"},
    {"start_ms": 1800, "end_ms": 3000, "text": "改造后更通透"},
]
SOURCE_HASH = hashlib.sha256(
    json.dumps(SEGMENTS, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
).hexdigest()


def _task(action="create_enqueue_and_collect_subtitles", path="WP-LOCAL-SUBTITLE-EXPORT"):
    return Task(
        goal_id="p13-subtitle", title="User-provided subtitle to SRT/VTT",
        worker="cloudtech-v4-adapter",
        input_payload={
            "action": action, "tenant_id": "tenant-subtitle",
            "path_id": path, "input_bindings": {"segments": SEGMENTS},
        },
    )


def _mock_transport(*, wrong_hash=False, fail_job=False):
    def handle(req):
        if req.url.path.endswith("/preflight"):
            return httpx.Response(200, json={
                "path_id": "WP-LOCAL-SUBTITLE-EXPORT", "revision": 1,
                "level": "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION",
            })
        if req.url.path == "/v4/workpaths/runs" and req.method == "POST":
            return httpx.Response(200, json={"run_id": "wpr_subtitle123"})
        if req.url.path.endswith("/enqueue-local"):
            return httpx.Response(200, json={
                "run_id": "wpr_subtitle123", "state": "QUEUED",
                "storage": "SQLITE_LOCAL_DURABLE",
                "provider_called": False,
            })
        return httpx.Response(200, json={
            "run_id": "wpr_subtitle123", "status": "FAILED" if fail_job else "COMPLETED",
            "nodes": [{
                "node_id": "subtitle_export",
                "operation": "subtitle.format_supplied",
                "status": "COMPLETED",
                "cost_cents": 0,
                "input_hash": "0" * 64 if wrong_hash else SOURCE_HASH,
                "output_ref": {
                    "srt": "1\n00:00:00,000 --> 00:00:01,500\n改造前空间狭小",
                    "vtt": "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\n改造前空间狭小",
                    "source_sha256": SOURCE_HASH,
                    "source": "user_supplied_timestamped_transcript",
                    "segment_count": 2,
                    "mock": False, "asr_performed": False, "model_called": False,
                },
            }],
        })
    return httpx.MockTransport(handle)


@pytest.mark.asyncio
async def test_actual_queue_receipt_results_in_hash_checked_srt_vtt(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_V4_JWT_SECRET", raising=False)
    monkeypatch.delenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", raising=False)
    async with httpx.AsyncClient(transport=_mock_transport()) as client:
        worker = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        output = await worker.execute(_task())
    assert output.inline_json["business_validated"] is False
    assert output.inline_json["data"]["source_verified_locally"] is True
    assert output.inline_json["data"]["local_execution"]["nodes"][0]["output_ref"]["asr_performed"] is False
    assert len(output.inline_json["data"]["output_sha256"]) == 64


@pytest.mark.asyncio
async def test_forged_subtitle_input_hash_is_rejected(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_V4_JWT_SECRET", raising=False)
    monkeypatch.delenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", raising=False)
    async with httpx.AsyncClient(
        transport=_mock_transport(wrong_hash=True),
    ) as client:
        worker = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        with pytest.raises(ValueError, match="lacks verified source"):
            await worker.execute(_task())


@pytest.mark.asyncio
async def test_failed_local_queue_never_claims_subtitle_success(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_V4_JWT_SECRET", raising=False)
    monkeypatch.delenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", raising=False)
    async with httpx.AsyncClient(
        transport=_mock_transport(fail_job=True),
    ) as client:
        worker = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        with pytest.raises(ValueError, match="worker failed"):
            await worker.execute(_task())


@pytest.mark.asyncio
async def test_subtitle_action_cannot_be_redirected_to_other_path(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_V4_JWT_SECRET", raising=False)
    monkeypatch.delenv("CLOUDTECH_V4_REQUIRE_TENANT_JWT", raising=False)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: (_ for _ in ()).throw(AssertionError("should not contact network"))
    )) as client:
        worker = CloudTechV4Adapter(
            base_url="https://cloudtech.example", client=client,
        )
        with pytest.raises(ValueError, match="only supports"):
            await worker.execute(_task(path="WP-BLOGGER-RESEARCH"))
