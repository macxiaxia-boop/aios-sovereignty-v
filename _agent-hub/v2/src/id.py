# v2/src/id.py — id and hashing helpers.
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now_iso() -> str:
    """ISO8601 UTC with Z suffix. e.g. 2026-09-29T12:00:00Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def idempotency_key(sender: str, recipient: str, message_type: str, payload: dict) -> str:
    """sha256(canonical sender|recipient|message_type|payload)."""
    s = f"{sender}|{recipient}|{message_type}|" + canonical_json(payload)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def is_uuid(s: str) -> bool:
    return isinstance(s, str) and bool(UUID_RE.match(s))


def is_sha256(s: str) -> bool:
    return isinstance(s, str) and bool(SHA256_RE.match(s))