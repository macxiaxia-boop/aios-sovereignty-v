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


# ---------------------------------------------------------------- R286
# Chunked large-text support.  An envelope whose payload contains text longer
# than `max_chunk_size` bytes MUST be split into chunked envelopes carrying
# `payload.text_chunks[]` instead of putting raw bytes in the queue.  The
# receiver reassembles them via `envelope_from_chunks(chunks)` keyed by
# `correlation_id` (== parent.id).
#
# Hard rule (R286.A): raw binary MUST NEVER appear in any envelope payload.
# Artifact references (path + sha256 + content_type) are the only allowed
# way to ship large content through the queue.
DEFAULT_CHUNK_SIZE = 32768  # 32 KiB per chunk (R286 decision: chunk size default 32 KiB)
MAX_CHUNK_TEXT_BYTES = 65536  # 64 KiB threshold to trigger chunking


def envelope_to_chunks(env: dict, *, max_chunk_size: int = DEFAULT_CHUNK_SIZE) -> list:
    """Split `env.payload.text` into multiple chunk envelopes.

    Returns the list of chunk envelopes (each carries `payload.text_chunks`
    with a single entry).  The original envelope is NOT mutated; chunks are
    fresh envelopes whose `correlation_id` == parent.id and `in_reply_to` ==
    parent.id.  Returns [] when text fits in one chunk (no chunking needed).

    Each chunk envelope is independently valid against envelope v1.0 (the
    optional `text_chunks` field is allowed per envelope.schema.json).
    The chunk envelope's idempotency_key is computed from its actual
    payload so verify_envelope can re-validate it consistently.
    """
    text = (env.get("payload") or {}).get("text")
    if not isinstance(text, str):
        return []
    if len(text.encode("utf-8")) <= max_chunk_size:
        return []
    parent_id = env["id"]
    encoded = text.encode("utf-8")
    chunk_total = (len(encoded) + max_chunk_size - 1) // max_chunk_size
    chunks = []
    for i in range(chunk_total):
        start = i * max_chunk_size
        end = min(start + max_chunk_size, len(encoded))
        chunk_text = encoded[start:end].decode("utf-8", errors="replace")
        chunk_payload = {
            "text_chunks": [{
                "chunk_id": parent_id,
                "chunk_index": i,
                "chunk_total": chunk_total,
                "text": chunk_text,
                "correlation_id": parent_id,
            }],
            "is_chunk": True,
            "parent_envelope_id": parent_id,
        }
        chunk_env = {
            "id": new_uuid(),
            "schema_version": "1.0",
            "message_type": env["message_type"],
            "sender": env["sender"],
            "recipient": env["recipient"],
            "timestamp": utc_now_iso(),
            "idempotency_key": idempotency_key(
                env["sender"], env["recipient"], env["message_type"], chunk_payload,
            ),
            "payload": chunk_payload,
            "correlation_id": parent_id,
            "in_reply_to": parent_id,
            "ttl_ms": env.get("ttl_ms", 300000),
        }
        chunks.append(chunk_env)
    return chunks


def envelope_from_chunks(chunks: list) -> dict:
    """Reassemble a parent envelope from N chunk envelopes.

    Chunks MUST share the same `correlation_id` (== parent.id) AND the same
    `chunk_total`.  Indices must be 0..chunk_total-1 with no duplicates and
    no gaps.  Returns the assembled parent envelope (with reconstructed
    payload.text).  Raises ValueError on any of these invariant violations.
    """
    if not chunks:
        raise ValueError("envelope_from_chunks requires at least 1 chunk")
    parent_id = chunks[0].get("correlation_id")
    if parent_id is None:
        raise ValueError("first chunk missing correlation_id (== parent envelope id)")
    chunk_total = None
    sorted_chunks = []
    seen_indices = set()
    for c in chunks:
        cid = c.get("correlation_id")
        if cid != parent_id:
            raise ValueError(
                f"chunk {c.get('id')!r} has correlation_id={cid!r}, "
                f"expected {parent_id!r}"
            )
        chunks_arr = (c.get("payload") or {}).get("text_chunks") or []
        if not chunks_arr:
            raise ValueError(
                f"chunk {c.get('id')!r} has no payload.text_chunks[]"
            )
        for chunk_meta in chunks_arr:
            if chunk_meta.get("chunk_id") != parent_id:
                raise ValueError(
                    f"chunk {chunk_meta.get('chunk_id')!r} does not match parent {parent_id!r}"
                )
            ct = chunk_meta.get("chunk_total")
            ci = chunk_meta.get("chunk_index")
            if chunk_total is None:
                chunk_total = ct
            elif chunk_total != ct:
                raise ValueError(
                    f"inconsistent chunk_total: was {chunk_total}, now {ct}"
                )
            if ci in seen_indices:
                raise ValueError(f"duplicate chunk_index={ci}")
            seen_indices.add(ci)
            sorted_chunks.append((ci, chunk_meta))
    expected_range = set(range(chunk_total))
    missing = expected_range - seen_indices
    if missing:
        raise ValueError(f"missing chunk indices: {sorted(missing)}")
    sorted_chunks.sort(key=lambda x: x[0])
    full_text = "".join(meta["text"] for _, meta in sorted_chunks)
    first = chunks[0]
    parent = {
        "id": parent_id,
        "schema_version": "1.0",
        "message_type": first["message_type"],
        "sender": first["sender"],
        "recipient": first["recipient"],
        "timestamp": first["timestamp"],
        "idempotency_key": first.get("idempotency_key", ""),
        "payload": {
            "text": full_text,
            "is_chunked_reassembly": True,
            "chunk_total": chunk_total,
        },
        "ttl_ms": first.get("ttl_ms", 300000),
        "reassembled_from_chunks": True,
    }
    if "correlation_id" in first and first.get("in_reply_to") != parent_id:
        parent["in_reply_to"] = first.get("in_reply_to")
    return parent


def verify_envelope(env: dict) -> tuple:
    """Validate envelope structure AND idempotency_key consistency."""
    ok, errors = validate_envelope(env)
    if not ok:
        return False, errors
    expected = idempotency_key(env["sender"], env["recipient"], env["message_type"], env["payload"])
    if expected != env["idempotency_key"]:
        return False, [f"idempotency_key mismatch: expected {expected[:16]}... got {env['idempotency_key'][:16]}..."]
    return True, []