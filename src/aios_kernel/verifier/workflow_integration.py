"""workflow_integration.py - verify_step for T0033 Workflow (T0035 Section 7).

The T0033 WorkflowEngine drives steps through a DAG; each step has an
Activity. After a "task activity" completes, the workflow needs to
verify the task's output before letting downstream steps run.

This module provides:
- make_verify_activity(verifier, task_id_fn) -> CallableActivity
  that wraps a Verifier as a WorkflowStep.Activity. The activity looks
  up the task by id (via task_id_fn), runs the verifier, and returns
  ActivityResult(success=verdict.is_pass, output={verdict, ...}).
  The WorkflowEngine then naturally routes Verifier FAIL responses to
  the configured retry policy.

- make_remote_verify_activity(http_url, ...) -> CallableActivity
  variant that calls a remote Verifier over HTTP (the canonical T0035
  integration). Used when the Verifier is in its own process.

Example wiring (T0033-style):

    from aios_kernel.verifier import (
        DeterministicVerifier, InMemoryEvidenceStore,
    )
    from aios_kernel.verifier.workflow_integration import make_remote_verify_activity

    store = InMemoryEvidenceStore()
    local_v = DeterministicVerifier("local", store)
    verify = make_verify_activity(local_v, task_id_fn=lambda ctx: ctx.input["task_id"])

    # or, the canonical out-of-process form:
    remote_verify = make_remote_verify_activity("http://127.0.0.1:9001")
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx

from aios_kernel.verifier.protocol import Verdict, VerdictCode, Verifier
from aios_kernel.workflows.step import (
    ActivityContext,
    ActivityResult,
    CallableActivity,
)

log = logging.getLogger("aios_kernel.verifier.workflow_integration")


# ---------- helpers --------------------------------------------------------


def _verdict_to_activity_result(verdict: Verdict) -> ActivityResult:
    """Map a Verifier Verdict to the engine's ActivityResult.

    Mapping:
        PASS    -> success=True (engine records completed, downstream runs)
        FAIL    -> success=False, error=reason (engine triggers retry policy)
        BLOCKED -> success=False, error=reason (engine triggers retry policy)

    The full verdict is in output for downstream steps to inspect.
    """
    success = verdict.verdict == VerdictCode.PASS
    return ActivityResult(
        success=success,
        output={
            "verdict_code": verdict.verdict.value,
            "verdict_id": verdict.verifier_id,
            "verdict_reason": verdict.reason,
            "verdict_details": verdict.details,
            "verdict_signed_at": verdict.signed_at.isoformat()
            if verdict.signed_at
            else None,
            "task_id": verdict.task_id,
        },
        error=None if success else (verdict.error or verdict.reason or "verifier rejected"),
    )


# ---------- in-process factory ---------------------------------------------


def make_verify_activity(
    verifier: Verifier,
    *,
    task_id_fn: Callable[[ActivityContext], str] | None = None,
    evidence_ids_fn: Callable[[ActivityContext], list[str]] | None = None,
    task_projection_fn: Callable[[ActivityContext], dict[str, Any]] | None = None,
) -> CallableActivity:
    """Wrap a Verifier as a WorkflowStep Activity.

    Args:
        verifier: any Verifier protocol implementation
        task_id_fn: how to extract the task id from ActivityContext.
                    Default: ctx.input["task_id"]
        evidence_ids_fn: how to extract evidence ids from ActivityContext.
                         Default: ctx.input.get("evidence_ids", [])
        task_projection_fn: how to build the task dict for the verifier.
                            Default: {**ctx.input, "id": task_id}
    """
    _task_id_fn = task_id_fn or (lambda ctx: str(ctx.input.get("task_id") or ""))
    _evidence_ids_fn = evidence_ids_fn or (lambda ctx: list(ctx.input.get("evidence_ids") or []))
    _task_proj_fn = task_projection_fn or (
        lambda ctx: {**ctx.input, "id": _task_id_fn(ctx)}
    )

    async def _run(ctx: ActivityContext) -> ActivityResult:
        task_id = _task_id_fn(ctx)
        evidence_ids = _evidence_ids_fn(ctx)
        task = _task_proj_fn(ctx)
        verdict = await verifier.verify(task, evidence_ids)
        log.info(
            "verify_step: task=%s verifier=%s verdict=%s reason=%s",
            task_id,
            verdict.verifier_id,
            verdict.verdict.value,
            verdict.reason,
        )
        return _verdict_to_activity_result(verdict)

    return CallableActivity(name="verify_step", fn=_run)


# ---------- out-of-process factory ----------------------------------------


def make_remote_verify_activity(
    url: str = "http://127.0.0.1:9001",
    *,
    timeout_s: float = 30.0,
    verifier_id: str | None = None,
) -> CallableActivity:
    """Wrap a remote Verifier (running in another process) as a WorkflowStep Activity.

    The activity POSTs to {url}/verify with the task projection and
    returns ActivityResult(success=verdict.is_pass, ...). On connection
    errors the activity returns success=False with a BLOCKED-style error
    (engine will retry per RetryPolicy).

    Args:
        url: base URL of the remote Verifier (no trailing slash)
        timeout_s: per-request timeout in seconds
        verifier_id: optional id to stamp on the request; server may
                     override with its own if not provided
    """
    async def _run(ctx: ActivityContext) -> ActivityResult:
        task_id = str(ctx.input.get("task_id") or "")
        task = {**ctx.input, "id": task_id}
        payload: dict[str, Any] = {"task": task}
        if verifier_id:
            payload["verifier_id"] = verifier_id
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                resp = await client.post(f"{url.rstrip('/')}/verify", json=payload)
        except httpx.HTTPError as exc:
            log.warning("verify_step: HTTP error to %s: %s", url, exc)
            return ActivityResult(
                success=False,
                error=f"verifier_unreachable: {type(exc).__name__}: {exc}",
            )
        if resp.status_code != 200:
            return ActivityResult(
                success=False,
                error=f"verifier_http_{resp.status_code}: {resp.text[:200]}",
            )
        body = resp.json()
        verdict_payload = body.get("verdict", {})
        try:
            verdict = Verdict.model_validate(verdict_payload)
        except Exception as exc:  # noqa: BLE001
            return ActivityResult(
                success=False,
                error=f"verifier_response_malformed: {type(exc).__name__}: {exc}",
            )
        log.info(
            "verify_step: task=%s remote_verifier_pid=%s verdict=%s reason=%s",
            task_id,
            body.get("verifier_pid"),
            verdict.verdict.value,
            verdict.reason,
        )
        return _verdict_to_activity_result(verdict)

    return CallableActivity(name="verify_step_remote", fn=_run)


# ---------- health-check helper for tests ----------------------------------


async def remote_health(url: str = "http://127.0.0.1:9001", timeout_s: float = 5.0) -> dict:
    """Hit GET {url}/health and return the parsed JSON body.

    Raises httpx.HTTPError on connection problems. Used by integration
    tests to confirm the Verifier process is up before posting /verify.
    """
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.get(f"{url.rstrip('/')}/health")
        resp.raise_for_status()
        return resp.json()


__all__ = [
    "make_verify_activity",
    "make_remote_verify_activity",
    "remote_health",
]
