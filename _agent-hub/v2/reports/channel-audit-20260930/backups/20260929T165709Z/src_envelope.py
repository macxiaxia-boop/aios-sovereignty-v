# v2/src/envelope.py — build, reply, and verify envelopes.
from __future__ import annotations

import json
from typing import Optional

from .id import idempotency_key, new_uuid, utc_now_iso
from .validation import validate_envelope

VALID_TYPES = ("message", "task", "status", "result", "ack", "heartbeat", "error")


def build_envelope(
    sender: str,
    recipient: str,
    message_type: str,
    payload: dict,
    *,
    correlation_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    artifact_refs: Optional[list] = None,
    retry_count: int = 0,
    ttl_ms: int = 300000,
) -> dict:
    """Construct a v1.0 envelope. Computes idempotency_key automatically."""
    if message_type not in VALID_TYPES:
        raise ValueError(f"message_type {message_type!r} not in {VALID_TYPES}")
    env = {
        "id": new_uuid(),
        "schema_version": "1.0",
        "message_type": message_type,
        "sender": sender,
        "recipient": recipient,
        "timestamp": utc_now_iso(),
        "idempotency_key": idempotency_key(sender, recipient, message_type, payload),
        "payload": payload,
        "retry_count": retry_count,
        "ttl_ms": ttl_ms,
    }
    if correlation_id is not None:
        env["correlation_id"] = correlation_id
    if in_reply_to is not None:
        env["in_reply_to"] = in_reply_to
    if artifact_refs:
        env["artifact_refs"] = artifact_refs
    ok, errors = validate_envelope(env)
    if not ok:
        raise ValueError(f"built envelope invalid: {errors}")
    return env


def reply_envelope(
    original: dict,
    sender: str,
    message_type: str,
    payload: dict,
    *,
    ttl_ms: Optional[int] = None,
) -> dict:
    """Build a reply envelope (status/result/ack/error) tied to original.id."""
    if message_type not in ("status", "result", "ack", "error"):
        raise ValueError(f"reply_envelope only supports status/result/ack/error, got {message_type!r}")
    return build_envelope(
        sender=sender,
        recipient=original.get("sender", "broadcast"),
        message_type=message_type,
        payload=payload,
        correlation_id=original["id"],
        in_reply_to=original["id"],
        ttl_ms=ttl_ms if ttl_ms is not None else original.get("ttl_ms", 300000),
    )


def envelope_to_json(env: dict) -> str:
    return json.dumps(env, ensure_ascii=False, indent=2, sort_keys=True)


def envelope_from_json(text: str) -> dict:
    return json.loads(text)


def verify_envelope(env: dict) -> tuple:
    """Validate envelope structure AND idempotency_key consistency."""
    ok, errors = validate_envelope(env)
    if not ok:
        return False, errors
    expected = idempotency_key(env["sender"], env["recipient"], env["message_type"], env["payload"])
    if expected != env["idempotency_key"]:
        return False, [f"idempotency_key mismatch: expected {expected[:16]}... got {env['idempotency_key'][:16]}..."]
    return True, []