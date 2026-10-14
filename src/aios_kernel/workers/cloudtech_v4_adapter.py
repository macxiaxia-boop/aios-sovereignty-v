"""AIOS worker for the EXISTING CloudTech V4 HTTP workpath API.

Only read-only preflight and deterministic, zero-cost local-prefix execution
are allowed here. No posting, paid media, user impersonation or deployment.
The result is a verifiable JSON Artifact, NOT a business validation verdict.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from aios_kernel.domain.artifact import Artifact, ArtifactType
from aios_kernel.workers.base import HealthReport, HealthStatus


class CloudTechV4Adapter:
    worker_id = "cloudtech-v4-adapter"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        bearer_token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        uri = base_url or os.environ.get("CLOUDTECH_V4_BASE_URL", "")
        parsed = urlsplit(uri)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("CLOUDTECH_V4_BASE_URL must be explicitly configured")
        self._base_url = uri.rstrip("/")
        self._bearer_token = bearer_token or os.environ.get("CLOUDTECH_V4_BEARER_TOKEN")
        # An environment-scoped service signer MUST bind each request to its
        # own tenant. A shared static Bearer token cannot authorize 2 tenants.
        self._tenant_secret = os.environ.get("CLOUDTECH_V4_JWT_SECRET")
        self._require_signed = (
            os.environ.get("CLOUDTECH_V4_REQUIRE_TENANT_JWT", "0")
            .strip().lower() in {"1", "true", "yes"}
        )
        if self._tenant_secret is not None and len(self._tenant_secret.encode()) < 32:
            raise ValueError("CLOUDTECH_V4_JWT_SECRET needs at least 32 bytes")
        if self._require_signed and not self._tenant_secret:
            raise ValueError("CLOUDTECH_V4_REQUIRE_TENANT_JWT requires a signing secret")
        self._client_owned = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url, timeout=25.0, follow_redirects=False,
        )

    def _headers(self, tenant_id: str | None = None) -> dict[str, str]:
        if tenant_id and self._tenant_secret:
            def segment(value: dict) -> str:
                return base64.urlsafe_b64encode(
                    json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
                ).rstrip(b"=").decode()

            issued = int(time.time())
            header = segment({"alg": "HS256", "typ": "JWT"})
            payload = segment({
                "tenant_id": tenant_id,
                "user_id": "aios-v4-service-worker",
                "permissions": ["v4:local-only"],
                "iat": issued,
                "exp": issued + 120,
            })
            body = f"{header}.{payload}"
            signature = base64.urlsafe_b64encode(
                hmac.new(self._tenant_secret.encode(), body.encode(), hashlib.sha256).digest()
            ).rstrip(b"=").decode()
            return {"Authorization": f"Bearer {body}.{signature}"}
        if self._require_signed and tenant_id:
            raise ValueError("signed tenant credentials required")
        if self._bearer_token:
            return {"Authorization": f"Bearer {self._bearer_token}"}
        return {}

    async def _call(
        self, method: str, path: str, *,
        tenant_id: str | None = None, **kwargs,
    ) -> dict:
        response = await self._client.request(
            method, self._base_url + path,
            headers=self._headers(tenant_id=tenant_id), **kwargs,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("CloudTech API must return a JSON object")
        return data

    async def execute(self, task) -> Artifact:
        payload = getattr(task, "input_payload", {}) or {}
        action = payload.get("action")
        path_id = payload.get("path_id")
        tenant_id = payload.get("tenant_id")
        if action not in {
            "preflight", "create_and_execute_local", "create_enqueue_and_collect_subtitles",
        }:
            raise ValueError("CloudTech worker only allows read-only/local actions")
        if not path_id or not tenant_id:
            raise ValueError("CloudTech worker needs path_id and tenant_id")
        if not isinstance(path_id, str) or not re.fullmatch(
            r"WP-[A-Z0-9]+(?:-[A-Z0-9]+)*", path_id
        ):
            raise ValueError("invalid CloudTech workpath ID")
        if not isinstance(tenant_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,64}", tenant_id
        ):
            raise ValueError("invalid CloudTech tenant ID")

        preflight = await self._call(
            "GET", f"/v4/workpaths/{path_id}/preflight",
        )
        if (
            preflight.get("path_id") != path_id
            or preflight.get("level") != "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION"
        ):
            raise ValueError("CloudTech capability preflight identity mismatch")

        if action == "create_enqueue_and_collect_subtitles" and path_id != "WP-LOCAL-SUBTITLE-EXPORT":
            raise ValueError("subtitle enqueue action only supports WP-LOCAL-SUBTITLE-EXPORT")
        remote: dict = {"preflight": preflight}
        if action in {"create_and_execute_local", "create_enqueue_and_collect_subtitles"}:
            inputs = payload.get("input_bindings", {})
            if not isinstance(inputs, dict):
                raise ValueError("input_bindings must be a dictionary")
            created = await self._call(
                "POST", "/v4/workpaths/runs",
                tenant_id=tenant_id,
                params={"tenant_id": tenant_id},
                json={
                    "path_id": path_id,
                    "revision": preflight["revision"],
                    "input_bindings": inputs,
                    "idempotency_key": str(task.id),
                },
            )
            run_id = created.get("run_id")
            if not isinstance(run_id, str) or not run_id.startswith("wpr_"):
                raise ValueError("CloudTech create_run did not return a valid run id")
            if action == "create_enqueue_and_collect_subtitles":
                # CloudTech's original durable local worker must run separately.
                # Enqueue is NOT completion; wait for actual persisted receipt.
                queue = await self._call(
                    "POST", f"/v4/workpaths/runs/{run_id}/enqueue-local",
                    tenant_id=tenant_id, params={"tenant_id": tenant_id},
                )
                if (
                    queue.get("run_id") != run_id
                    or queue.get("storage") != "SQLITE_LOCAL_DURABLE"
                    or queue.get("provider_called") is not False
                ):
                    raise ValueError("CloudTech local queue attestation invalid")
                remote["enqueue"] = queue
                completed = None
                for _ in range(70):
                    snapshot = await self._call(
                        "GET", f"/v4/workpaths/runs/{run_id}",
                        tenant_id=tenant_id, params={"tenant_id": tenant_id},
                    )
                    if snapshot.get("run_id") != run_id:
                        raise ValueError("CloudTech readback run identity mismatch")
                    if snapshot.get("status") == "COMPLETED":
                        completed = snapshot
                        break
                    if snapshot.get("status") in {"FAILED", "CANCELED"}:
                        raise ValueError("CloudTech local subtitle worker failed")
                    await asyncio.sleep(0.2)
                if completed is None:
                    raise TimeoutError(
                        "CloudTech subtitle run not completed; stored run remains available"
                    )
                segments = inputs.get("segments")
                if not isinstance(segments, list) or not segments:
                    raise ValueError("supplied subtitle segments are missing")
                clean = []
                last_end = 0
                for i, segment in enumerate(segments):
                    if not isinstance(segment, dict):
                        raise ValueError(f"invalid segment {i}")
                    start = segment.get("start_ms")
                    end = segment.get("end_ms")
                    value = segment.get("text")
                    if (
                        not isinstance(start, int) or isinstance(start, bool)
                        or not isinstance(end, int) or isinstance(end, bool)
                        or start < last_end or end <= start or end > 86_400_000
                        or not isinstance(value, str)
                    ):
                        raise ValueError(f"invalid subtitle timing {i}")
                    normalized = " ".join(
                        "".join(
                            ch if ch >= " " and ch != "\x7f" else " "
                            for ch in value
                        ).split()
                    )
                    if not normalized:
                        raise ValueError(f"empty subtitle segment {i}")
                    clean.append({
                        "start_ms": start, "end_ms": end, "text": normalized,
                    })
                    last_end = end
                canonical = json.dumps(
                    clean, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                )
                source_hash = hashlib.sha256(canonical.encode()).hexdigest()
                nodes = completed.get("nodes")
                node = nodes[0] if isinstance(nodes, list) and len(nodes) == 1 else {}
                output = node.get("output_ref") if isinstance(node, dict) else None
                if not (
                    node.get("node_id") == "subtitle_export"
                    and node.get("operation") == "subtitle.format_supplied"
                    and node.get("status") == "COMPLETED"
                    and node.get("cost_cents") == 0
                    and node.get("input_hash") == source_hash
                    and isinstance(output, dict)
                    and output.get("source_sha256") == source_hash
                    and output.get("mock") is False
                    and output.get("asr_performed") is False
                    and output.get("model_called") is False
                    and output.get("source") == "user_supplied_timestamped_transcript"
                    and output.get("segment_count") == len(clean)
                    and isinstance(output.get("srt"), str) and output["srt"]
                    and isinstance(output.get("vtt"), str) and output["vtt"]
                ):
                    raise ValueError("CloudTech subtitle receipt lacks verified source")
                remote["local_execution"] = completed
                remote["source_verified_locally"] = True
                remote["output_sha256"] = hashlib.sha256(
                    json.dumps(output, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
            else:
                executed = await self._call(
                    "POST", f"/v4/workpaths/runs/{run_id}/execute-local",
                    tenant_id=tenant_id,
                    params={"tenant_id": tenant_id},
                )
                if path_id == "WP-LOCAL-ARTICLE-EXTRACT":
                    # Newer CloudTech V4 uses a durable, genuine user-supplied
                    # HTML parser rather than the earlier URL-only prefix.
                    # Do not accept a shaped SUCCESS without source provenance.
                    source = inputs.get("html")
                    expected_hash = (
                        hashlib.sha256(source.encode()).hexdigest()
                        if isinstance(source, str) else None
                    )
                    nodes = executed.get("nodes")
                    node = nodes[0] if isinstance(nodes, list) and len(nodes) == 1 else {}
                    result_ref = node.get("output_ref") if isinstance(node, dict) else None
                    if not (
                        executed.get("run_id") == run_id
                        and executed.get("status") == "COMPLETED"
                        and executed.get("worker_type") == "SYNCHRONOUS_LOCAL_ONLY"
                        and executed.get("provider_called") is False
                        and executed.get("cost_cents") == 0
                        and node.get("node_id") == "html_parse"
                        and node.get("operation") == "article.html_parse"
                        and node.get("status") == "COMPLETED"
                        and node.get("input_hash") == expected_hash
                        and node.get("cost_cents") == 0
                        and isinstance(result_ref, dict)
                        and result_ref.get("mock") is False
                        and result_ref.get("retrieval_policy") == "supplied_html_only"
                        and result_ref.get("content_sha256") == expected_hash
                    ):
                        raise ValueError("CloudTech HTML extraction lacks verifiable source provenance")
                    remote["source_verified_locally"] = True
                    remote["output_sha256"] = hashlib.sha256(
                        json.dumps(result_ref, sort_keys=True, ensure_ascii=False).encode()
                    ).hexdigest()
                    remote["storage"] = executed.get("storage", "UNVERIFIED")
                elif (
                    executed.get("run_id") != run_id
                    or executed.get("external_calls") != 0
                    or executed.get("charged_cents") != 0
                    or executed.get("durability") != "IN_PROCESS_ONLY_NOT_PRODUCTION_DURABLE"
                ):
                    raise ValueError("CloudTech local execution violated zero-side-effect contract")
            remote["created_run"] = created
            if action == "create_and_execute_local":
                remote["local_execution"] = executed

        out = {
            "platform": "cloudtech-v4",
            "path_id": path_id,
            "tenant_id": tenant_id,
            "action": action,
            "state": "PATH_PREFLIGHT_OR_PARTIAL_ONLY",
            "business_validated": False,
            "provider_call_allowed": False,
            "data": remote,
        }
        encoded = json.dumps(out, sort_keys=True, ensure_ascii=False, default=str)
        return Artifact(
            task_id=str(task.id), artifact_type=ArtifactType.JSON,
            label="cloudtech-v4-auditable-result",
            inline_json=out,
            hash_sha256=hashlib.sha256(encoded.encode()).hexdigest(),
            size_bytes=len(encoded.encode()),
            mime_type="application/json",
            metadata={"verified": False, "source": self._base_url},
        )

    async def cancel(self, task_id):
        # No remote publishing/paid action exists in this worker.
        return None

    async def health(self):
        return HealthReport(
            worker_id=self.worker_id,
            status=HealthStatus.DEGRADED,
            last_check_at=datetime.now(UTC),
            message="Config present; remote health requires explicit preflight",
            metadata={"configured": True, "production_ready": False},
        )

    async def warmup(self):
        return None

    async def shutdown(self):
        if self._client_owned:
            await self._client.aclose()
