# v2/src/queue.py — file-based message queue with claim/ack/deadletter + idempotency dedup.
#
# Concurrency model (R320.1 hardened):
#   - One .json per envelope, filename = "<id>__<sender>__<recipient>__<message_type>.json"
#   - To claim: atomically rename <name>.json -> <name>.claimed.<host>.<pid>.<nonce>.json
#     using os.replace (atomic on POSIX and on Windows)
#   - To ack: remove the .claimed.* file
#   - To deadletter: rename .claimed.* -> <name>.dead.json
#   - Idempotency index lives in state/idempotency_index.json and is updated under
#     a cross-process file lock (src.lock.file_lock) keyed on the index file.
#     Every enqueue does read-modify-write inside the same critical section.
#   - Every tmp file is named with a unique uuid suffix so concurrent writers on the
#     same target do not collide (no more WinError 32 sharing violations).
from __future__ import annotations

import json
import os
import socket
import time
import uuid
from pathlib import Path
from typing import Optional

from .envelope import envelope_from_json, envelope_to_json, verify_envelope
from .lock import file_lock
from .paths import DEADLETTER, INBOX, OUTBOX, ensure_dirs, STATE_FILE
from .validation import validate_envelope

IDEMPOTENCY_INDEX_FILE = STATE_FILE.parent / "idempotency_index.json"
# R320.2 fix: lock an INDEPENDENT sidecar file, NOT the index itself.
# On Windows, locking the index file makes `os.replace(tmp, index)` fail
# with WinError 5 (cannot replace a locked file). Using a sidecar lock
# file means we lock the sidecar, mutate the index, then we release — and
# os.replace to the index file is never blocked.
IDEMPOTENCY_INDEX_LOCK = STATE_FILE.parent / "idempotency_index.json.lock"


def _read_idempotency_index_unlocked() -> dict:
    if not IDEMPOTENCY_INDEX_FILE.exists():
        return {}
    try:
        return json.loads(IDEMPOTENCY_INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_idempotency_index_unlocked(idx: dict) -> None:
    # Each write uses a unique tmp filename to avoid sharing-violation collisions
    # on Windows when multiple processes/threads write concurrently.
    ensure_dirs()
    unique = uuid.uuid4().hex
    tmp = IDEMPOTENCY_INDEX_FILE.with_name(
        IDEMPOTENCY_INDEX_FILE.name + f".tmp.{unique}.{os.getpid()}"
    )
    tmp.write_text(json.dumps(idx, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, IDEMPOTENCY_INDEX_FILE)


def _safe_filename(env: dict) -> str:
    return f"{env['id']}__{env['sender']}__{env['recipient']}__{env['message_type']}.json"


def enqueue(env: dict, *, dest: str = "inbox") -> dict:
    """Enqueue an envelope under cross-process lock. Returns {"envelope": env,
    "deduped": bool, "existing_id": Optional[str], "file": Optional[str]}.
    The check-and-write happens inside the same critical section."""
    ensure_dirs()
    ok, errors = verify_envelope(env)
    if not ok:
        raise ValueError(f"refusing to enqueue invalid envelope: {errors}")

    target_dir = INBOX if dest == "inbox" else OUTBOX
    target = None
    with file_lock(IDEMPOTENCY_INDEX_LOCK, timeout_s=30.0):
        idx = _read_idempotency_index_unlocked()
        key = env["idempotency_key"]
        if key in idx:
            return {"envelope": env, "deduped": True,
                    "existing_id": idx[key]["envelope_id"], "file": None}

        fname = _safe_filename(env)
        target = target_dir / fname
        # Atomic write via unique tmp + replace
        unique = uuid.uuid4().hex
        tmp = target.with_name(target.name + f".tmp.{unique}.{os.getpid()}")
        tmp.write_text(envelope_to_json(env), encoding="utf-8")
        os.replace(tmp, target)

        idx[key] = {
            "envelope_id": env["id"],
            "sender": env["sender"],
            "recipient": env["recipient"],
            "message_type": env["message_type"],
            "first_seen_at": env["timestamp"],
            "file": str(target.relative_to(target_dir.parent)),
        }
        _write_idempotency_index_unlocked(idx)
    return {"envelope": env, "deduped": False, "existing_id": None,
            "file": str(target.relative_to(target_dir.parent))}


def list_unclaimed(directory: Path = INBOX, limit: int = 100, *, recipient: Optional[str] = None) -> list:
    """Return unclaimed envelopes, optionally filtered by recipient.

    R320.3 fix: recipient filtering happens BEFORE the limit is applied,
    so an agent never misses its own messages when the queue is large.
    Use recipient=None or recipient="any" to disable filtering.
    """
    ensure_dirs()
    out = []
    for p in sorted(directory.glob("*.json")):
        # Skip tmp + claimed + dead sidecars
        if ".tmp." in p.name:
            continue
        if ".claimed." in p.name:
            continue
        if ".dead." in p.name:
            continue
        try:
            env = envelope_from_json(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        # recipient filter applied BEFORE limit, so an agent can always find
        # its own messages even when the queue has many messages for others.
        if recipient is not None and recipient != "any":
            env_recipient = env.get("recipient")
            # accept exact match or broadcast
            if env_recipient != recipient and env_recipient != "broadcast":
                continue
        out.append((p, env))
        if len(out) >= limit:
            break
    return out


def claim(env_path: Path, *, pid: Optional[int] = None) -> Optional[Path]:
    """Atomically claim an envelope for processing. Returns the new path or None if lost the race."""
    if not env_path.exists():
        return None
    nonce = uuid.uuid4().hex[:8]
    p = pid if pid is not None else os.getpid()
    host = socket.gethostname().split(".")[0][:16]
    new_name = env_path.name[:-5] + f".claimed.{host}.{p}.{nonce}.json"
    new_path = env_path.parent / new_name
    try:
        os.replace(env_path, new_path)
    except FileNotFoundError:
        return None
    except OSError:
        return None
    return new_path


def ack(claimed_path: Path) -> bool:
    try:
        os.remove(claimed_path)
        return True
    except FileNotFoundError:
        return False


def deadletter(claimed_path: Path, *, reason: str = "") -> Optional[Path]:
    ensure_dirs()
    if not claimed_path.exists():
        return None
    new_path = DEADLETTER / claimed_path.name.replace(".claimed.", ".dead.")
    try:
        os.replace(claimed_path, new_path)
        sidecar = new_path.with_name(new_path.name + ".reason.json")
        sidecar.write_text(json.dumps({"reason": reason,
                                        "moved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                                       ensure_ascii=False), encoding="utf-8")
        return new_path
    except OSError:
        return None


def get_envelope_by_id(envelope_id: str, *, scope: str = "inbox") -> Optional[dict]:
    base = INBOX if scope == "inbox" else OUTBOX
    for p in base.glob(f"{envelope_id}__*.json"):
        if ".tmp." in p.name or ".claimed." in p.name or ".dead." in p.name:
            continue
        try:
            return envelope_from_json(p.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None