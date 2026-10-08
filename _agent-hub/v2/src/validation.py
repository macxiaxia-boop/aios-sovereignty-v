# v2/src/validation.py — JSON Schema validation + manual envelope validation.
from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

from .id import UUID_RE, SHA256_RE
from .paths import SCHEMAS

ENVELOPE_TYPES = {"message", "task", "status", "result", "ack", "heartbeat", "error"}
TASK_STATES = {"queued", "running", "waiting", "succeeded", "failed", "cancelled"}
# Terminal = no further transitions allowed under any circumstance.
# `failed` is intentionally NOT terminal: it can transition back to `queued`
# for retry, as long as retry_count < max_retries. The state machine
# enforces that budget in transition().
TERMINAL_TASK_STATES = {"succeeded", "cancelled"}


def _load_schema(name: str) -> dict:
    p = SCHEMAS / name
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


_ENVELOPE_SCHEMA = None
_TASK_SCHEMA = None
_STATE_SCHEMA = None


def envelope_schema() -> dict:
    global _ENVELOPE_SCHEMA
    if _ENVELOPE_SCHEMA is None:
        _ENVELOPE_SCHEMA = _load_schema("envelope.schema.json")
    return _ENVELOPE_SCHEMA


def task_schema() -> dict:
    global _TASK_SCHEMA
    if _TASK_SCHEMA is None:
        _TASK_SCHEMA = _load_schema("task.schema.json")
    return _TASK_SCHEMA


def state_schema() -> dict:
    global _STATE_SCHEMA
    if _STATE_SCHEMA is None:
        _STATE_SCHEMA = _load_schema("state.schema.json")
    return _STATE_SCHEMA


def validate_envelope(env: dict) -> Tuple[bool, list]:
    """Lightweight validator: avoid external deps. Returns (ok, errors)."""
    errors = []
    if not isinstance(env, dict):
        return False, ["envelope must be a dict"]

    # required fields
    required = ["id", "schema_version", "message_type", "sender", "recipient",
                "timestamp", "idempotency_key", "payload"]
    for k in required:
        if k not in env:
            errors.append(f"missing required field: {k}")

    if "id" in env and not UUID_RE.match(str(env["id"])):
        errors.append("id must be uuid4 format")
    if "schema_version" in env and env["schema_version"] != "1.0":
        errors.append("schema_version must be '1.0'")
    if "message_type" in env and env["message_type"] not in ENVELOPE_TYPES:
        errors.append(f"message_type {env['message_type']!r} not in {ENVELOPE_TYPES}")
    if "sender" in env and not isinstance(env["sender"], str):
        errors.append("sender must be string")
    if "recipient" in env and not isinstance(env["recipient"], str):
        errors.append("recipient must be string")
    if "idempotency_key" in env and not SHA256_RE.match(str(env["idempotency_key"])):
        errors.append("idempotency_key must be sha256 hex (64 chars)")
    if "payload" in env and not isinstance(env["payload"], dict):
        errors.append("payload must be a dict")
    if "timestamp" in env and not isinstance(env["timestamp"], str):
        errors.append("timestamp must be string (ISO8601)")
    if "retry_count" in env:
        rc = env["retry_count"]
        if not isinstance(rc, int) or rc < 0:
            errors.append("retry_count must be non-negative int")
    if "ttl_ms" in env:
        ttl = env["ttl_ms"]
        if not isinstance(ttl, int) or ttl < 0:
            errors.append("ttl_ms must be non-negative int")
    if "artifact_refs" in env and not isinstance(env["artifact_refs"], list):
        errors.append("artifact_refs must be a list")
    if "correlation_id" in env and env["correlation_id"] is not None:
        if not UUID_RE.match(str(env["correlation_id"])):
            errors.append("correlation_id must be uuid4 format")
    if "additionalProperties" in env:
        # We don't store additionalProperties=false here; just sanity.
        pass
    return (len(errors) == 0, errors)


def validate_task(task: dict) -> Tuple[bool, list]:
    errors = []
    if not isinstance(task, dict):
        return False, ["task must be a dict"]
    required = ["task_id", "title", "state", "assignee", "created_at", "updated_at",
                "retry_count", "max_retries", "timeout_ms"]
    for k in required:
        if k not in task:
            errors.append(f"missing required field: {k}")
    if "task_id" in task and not UUID_RE.match(str(task["task_id"])):
        errors.append("task_id must be uuid4 format")
    if "state" in task and task["state"] not in TASK_STATES:
        errors.append(f"state {task['state']!r} not in {TASK_STATES}")
    if "retry_count" in task and (not isinstance(task["retry_count"], int) or task["retry_count"] < 0):
        errors.append("retry_count must be non-negative int")
    if "max_retries" in task and (not isinstance(task["max_retries"], int) or task["max_retries"] < 0):
        errors.append("max_retries must be non-negative int")
    if "timeout_ms" in task and (not isinstance(task["timeout_ms"], int) or task["timeout_ms"] < 0):
        errors.append("timeout_ms must be non-negative int")
    return (len(errors) == 0, errors)