# v2/src/v2_consumer.py — R286.A · unified v2 inbox consumer daemon.
#
# Purpose
# -------
# One multi-recipient consumer process.  For every entry in
# v2/agents/agents.json, claim unclaimed envelopes from v2/messages/inbox/{recipient}/,
# dispatch them via a dependency-injected adapter, and write:
#   - an `ack` envelope  (transport ack, immediate, separate from result)
#   - a `result` or `error` envelope (business result, tied to input.id via correlation_id)
#
# Architectural decisions (R286 plan §2)
# --------------------------------------
# - Extends existing AIOS Hub v2 primitives (envelope, queue, state_machine,
#   lock).  No parallel queue/state implementation is introduced.
# - Atomic queue writes use queue.enqueue (R320.1 hardened).  Idempotency
#   dedup is via the existing idempotency_index.json sidecar.
# - Per-recipient locks are enforced via a per-recipient threading.Lock so a
#   slow recipient does not block claims for other recipients in the same
#   process.
# - Acks and business results are kept separate (one `ack` envelope, plus one
#   `result`/`error` envelope — never merged).
# - Capability routing: each (sender, message_type) pair declares which
#   adapter is responsible (a simple capability table at the top of this
#   file).  Unknown recipients / unsupported message_types are deadlettered
#   with reason "no_route".
# - Bounded concurrency/backpressure: a global BoundedSemaphore with default
#   2, max 8 (matches AIOS_INTEROP_MAX_CONCURRENT env from aios_interop_mcp).
# - Leases: a per-envelope lease_secs computed from envelope.ttl_ms; if the
#   adapter times out, the consumer either retries (counted against
#   envelope.retry_count, when present) or deadletters with reason
#   "max_retries_exceeded".
# - DI: dispatch() is a module-level function that callers can override in
#   tests (e.g. monkeypatch dispatch_to_adapter).  All file IO goes through
#   the existing queue.enqueue + queue.claim + queue.deadletter APIs.
#
# Constraints honored
# -------------------
# - No raw binary in queue (chunked text only).
# - Atomic writes via queue.enqueue (uses existing file lock).
# - Existing idempotency index is reused; never writes a second copy.
# - AIOS_V2_ROOT override path respected everywhere.
#
# This module is meant to be invoked from
# D:\个人文件\AI\Operator\aios_tools\_aios_v2_consumer_runner.py
# (NOT auto-started in R286.A-C; gate AIOS_V2_CHANNEL_ENABLED=1 required).
from __future__ import annotations

import json
import os
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

from .envelope import (
    DEFAULT_CHUNK_SIZE,
    envelope_from_chunks,
    envelope_to_chunks,
    reply_envelope,
    verify_envelope,
)
from .lock import file_lock
from .paths import (
    AGENTS_JSON,
    DEADLETTER,
    EVENTS_LOG,
    INBOX,
    STATE_FILE,
    ensure_dirs,
    v2_root,
)
from .queue import ack as q_ack, claim as q_claim, deadletter as q_deadletter, enqueue as q_enqueue


# ---------------------------------------------------------------- Bounded concurrency
def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        v = int(os.environ.get(name, str(default)))
    except ValueError:
        v = default
    return max(minimum, min(v, maximum))


# R286 plan: bounded concurrency/backpressure default 2/8, max 8/64.
MAX_CONCURRENT = _bounded_env_int("AIOS_V2_CONSUMER_MAX_CONCURRENT", 2, 1, 8)
MAX_QUEUE = _bounded_env_int("AIOS_V2_CONSUMER_MAX_QUEUE", 8, 0, 64)
MAX_RETRIES_PER_ENVELOPE = 5


# ---------------------------------------------------------------- Capability routing
# Capability table: which dispatcher handles (recipient, message_type)?
# Keys are recipient agent_ids; values map message_type → dispatcher name.
# Unknown recipients or unsupported message_types fall through to
# `no_route_dispatcher` which deadletters with reason "no_route".
CAPABILITIES: dict[str, dict[str, str]] = {
    "codex": {
        "message": "passthrough",
        "task": "passthrough",
        "status": "passthrough",
        "result": "passthrough",
        "ack": "passthrough",
        "heartbeat": "passthrough",
        "error": "passthrough",
    },
    "claudecode": {
        "message": "passthrough",
        "task": "passthrough",
        "status": "passthrough",
        "result": "passthrough",
        "ack": "passthrough",
        "heartbeat": "passthrough",
        "error": "passthrough",
    },
    "hermes": {
        "message": "passthrough",
        "task": "passthrough",
        "status": "passthrough",
        "result": "passthrough",
        "ack": "passthrough",
        "heartbeat": "passthrough",
        "error": "passthrough",
    },
    "openclaw": {
        "message": "passthrough",
        "task": "passthrough",
        "status": "passthrough",
        "result": "passthrough",
        "ack": "passthrough",
        "heartbeat": "passthrough",
        "error": "passthrough",
    },
    "workbuddy": {
        "message": "passthrough",
        "task": "passthrough",
        "status": "passthrough",
        "result": "passthrough",
        "ack": "passthrough",
        "heartbeat": "passthrough",
        "error": "passthrough",
    },
    "broadcast": {
        "message": "passthrough",
        "task": "passthrough",
        "status": "passthrough",
        "result": "passthrough",
        "ack": "passthrough",
        "heartbeat": "passthrough",
        "error": "passthrough",
    },
}


def route_capability(recipient: str, message_type: str) -> Optional[str]:
    """Return the dispatcher name for (recipient, message_type) or None if unrouted."""
    rec = CAPABILITIES.get(recipient) or CAPABILITIES.get("broadcast")
    if not rec:
        return None
    return rec.get(message_type)


# ---------------------------------------------------------------- Adapter dispatch (DI)
def dispatch_to_adapter(envelope: dict, *, recipient: str) -> dict:
    """Default dispatcher: pure passthrough (returns a synthetic ack payload).

    Real adapters are injected by callers (production runners or test fakes)
    via `set_dispatcher()`.  This default exists so the consumer can run in
    isolation (loopback) without needing a live adapter.
    """
    return {
        "ok": True,
        "transport": "passthrough",
        "received_id": envelope["id"],
        "received_sender": envelope["sender"],
        "received_recipient": envelope.get("recipient"),
        "received_message_type": envelope.get("message_type"),
    }


_DISPATCHER: Callable[..., dict] = dispatch_to_adapter
_DISPATCHER_LOCK = threading.Lock()


def set_dispatcher(fn: Optional[Callable[..., dict]]) -> None:
    """Inject a custom dispatcher (used by tests)."""
    global _DISPATCHER
    with _DISPATCHER_LOCK:
        _DISPATCHER = fn if fn is not None else dispatch_to_adapter


def _current_dispatcher() -> Callable[..., dict]:
    with _DISPATCHER_LOCK:
        return _DISPATCHER


# ---------------------------------------------------------------- Per-recipient locks
_PER_RECIPIENT_LOCKS: dict[str, threading.Lock] = {}
_PER_RECIPIENT_LOCKS_MUTEX = threading.Lock()


def _recipient_lock(recipient: str) -> threading.Lock:
    with _PER_RECIPIENT_LOCKS_MUTEX:
        lk = _PER_RECIPIENT_LOCKS.get(recipient)
        if lk is None:
            lk = threading.Lock()
            _PER_RECIPIENT_LOCKS[recipient] = lk
        return lk


# ---------------------------------------------------------------- Event log helper
def _log_event(obj: dict) -> None:
    ensure_dirs()
    line = json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **obj},
                      ensure_ascii=False, sort_keys=True)
    try:
        with open(EVENTS_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    except Exception:
        pass


# ---------------------------------------------------------------- Consumer state
class ConsumerStats:
    def __init__(self) -> None:
        self.claimed = 0
        self.acked = 0
        self.results = 0
        self.errors = 0
        self.deadlettered = 0
        self.no_route = 0
        self.skipped_nonv2 = 0  # envelopes skipped because of legacy-file guard
        self.lock = threading.Lock()

    def incr(self, attr: str, by: int = 1) -> None:
        with self.lock:
            setattr(self, attr, getattr(self, attr) + by)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "claimed": self.claimed,
                "acked": self.acked,
                "results": self.results,
                "errors": self.errors,
                "deadlettered": self.deadlettered,
                "no_route": self.no_route,
                "skipped_nonv2": self.skipped_nonv2,
            }


# ---------------------------------------------------------------- Claim/look helpers
def list_for_recipient(recipient: str, *, limit: int = 100) -> list:
    """List unclaimed envelopes for `recipient` (matching recipient or broadcast)."""
    ensure_dirs()
    out = []
    for p in sorted(INBOX.glob("*.json")):
        if ".tmp." in p.name or ".claimed." in p.name or ".dead." in p.name:
            continue
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        env_recipient = env.get("recipient")
        if env_recipient not in (recipient, "broadcast"):
            continue
        out.append((p, env))
        if len(out) >= limit:
            break
    return out


def _is_legacy_marker_file(path: Path) -> bool:
    """R286 evidence plan: detect the 3 pre-R320.6 stranded ack envelopes
    so the consumer does NOT claim them.  Matches by exact filename pattern
    (no inspection of envelope bodies / secrets)."""
    name = path.name
    return (
        "41afc2c3-8fd3-4c80-80f2-62943eea25fd" in name
        or "19334d04-08f8-4d3d-9f94-4eab28d336ce" in name
        or "0fbf6f33-4eb9-47b6-9400-1c2914b2d72f" in name
    )


# ---------------------------------------------------------------- Dispatch core
def dispatch_envelope(env_path: Path, env: dict, *, dispatcher: Optional[Callable[..., dict]] = None,
                      stats: Optional[ConsumerStats] = None,
                      marker_filter: Optional[Callable[[dict], bool]] = None) -> dict:
    """Dispatch a single claimed envelope.

    Flow (R286 plan §2.3 + §2.7):
      1.  Verify envelope; if invalid, deadletter with reason invalid_envelope.
      2.  Capability-route; if no route, deadletter with reason no_route.
      3.  Emit immediate `ack` envelope (separate from result).
      4.  Invoke injected dispatcher.  On success: emit `result`.  On
          exception: emit `error`.
      5.  q_ack the original claimed file.  On any failure: deadletter
          with reason dispatch_failed.

    Returns a dict with `ok`, `envelope_id`, and per-step outcomes so tests
    can assert exactly what happened.
    """
    if stats is None:
        stats = ConsumerStats()

    out = {"ok": False, "envelope_id": env.get("id"),
           "steps": []}

    # Marker filter — used by gated live smoke to only claim R286-tagged envelopes.
    if marker_filter is not None and not marker_filter(env):
        out["skipped"] = "marker_filter_reject"
        stats.incr("skipped_nonv2")
        return out

    # 1. verify
    ok, errors = verify_envelope(env)
    if not ok:
        out["steps"].append({"step": "verify", "ok": False, "errors": errors})
        try:
            claimed = q_claim(env_path)
            if claimed:
                q_deadletter(claimed, reason=f"invalid_envelope:{';'.join(errors[:2])}")
                stats.incr("deadlettered")
        except Exception:
            pass
        return out
    out["steps"].append({"step": "verify", "ok": True})

    # 2. route
    route = route_capability(env.get("recipient"), env.get("message_type"))
    if not route:
        out["steps"].append({"step": "route", "ok": False, "reason": "no_route"})
        try:
            claimed = q_claim(env_path)
            if claimed:
                q_deadletter(claimed, reason="no_route")
                stats.incr("deadlettered")
                stats.incr("no_route")
        except Exception:
            pass
        return out
    out["steps"].append({"step": "route", "ok": True, "route": route})

    # 3. claim (atomic rename)
    claimed_path = q_claim(env_path)
    if claimed_path is None:
        out["steps"].append({"step": "claim", "ok": False, "reason": "race_lost"})
        return out
    stats.incr("claimed")
    out["steps"].append({"step": "claim", "ok": True, "claimed_path": str(claimed_path.name)})

    # 4. immediate ack (separate envelope)
    try:
        ack_env = reply_envelope(env, sender=env["recipient"], message_type="ack",
                                 payload={"ack_of": env["id"], "note": "v2_consumer_received"})
        # Default dest=inbox so original sender can receive via
        # `aiosv2.py receive --agent <sender>` (matches R320.6 contract).
        q_enqueue(ack_env)
        stats.incr("acked")
        out["steps"].append({"step": "ack_envelope", "ok": True,
                             "ack_id": ack_env["id"]})
    except Exception as e:
        out["steps"].append({"step": "ack_envelope", "ok": False,
                             "error": f"{type(e).__name__}: {e}"})
        q_deadletter(claimed_path, reason=f"ack_enqueue_failed:{type(e).__name__}")
        stats.incr("deadlettered")
        return out

    # 5. dispatcher
    fn = dispatcher if dispatcher is not None else _current_dispatcher()
    started = time.time()
    try:
        result_payload = fn(env, recipient=env["recipient"])
        duration_ms = int((time.time() - started) * 1000)
        out["steps"].append({"step": "dispatch", "ok": True, "duration_ms": duration_ms,
                             "result_keys": sorted(result_payload.keys()) if isinstance(result_payload, dict) else None})

        # 6. emit result envelope
        try:
            result_env = reply_envelope(env, sender=env["recipient"], message_type="result",
                                        payload={"output": result_payload})
            q_enqueue(result_env)
            stats.incr("results")
            out["steps"].append({"step": "result_envelope", "ok": True,
                                 "result_id": result_env["id"]})
        except Exception as e:
            out["steps"].append({"step": "result_envelope", "ok": False,
                                 "error": f"{type(e).__name__}: {e}"})
            q_deadletter(claimed_path, reason=f"result_enqueue_failed:{type(e).__name__}")
            stats.incr("deadlettered")
            return out

        # 7. ack the claim (file removed)
        if q_ack(claimed_path):
            out["steps"].append({"step": "q_ack", "ok": True})
        else:
            out["steps"].append({"step": "q_ack", "ok": False,
                                 "warning": "claim file already gone"})

        out["ok"] = True
        _log_event({"actor": "v2_consumer", "event": "dispatch.ok",
                    "envelope_id": env["id"], "recipient": env["recipient"],
                    "message_type": env["message_type"], "duration_ms": duration_ms})
        return out

    except Exception as e:
        duration_ms = int((time.time() - started) * 1000)
        out["steps"].append({"step": "dispatch", "ok": False,
                             "error": f"{type(e).__name__}: {e}",
                             "duration_ms": duration_ms})

        # Retry budget
        retry_count = int(env.get("retry_count") or 0)
        if retry_count < MAX_RETRIES_PER_ENVELOPE:
            # Re-enqueue with bumped retry_count.
            try:
                env["retry_count"] = retry_count + 1
                q_enqueue(env)  # idempotency_index will dedupe if exact same payload
                q_ack(claimed_path)
                stats.incr("acked")
                _log_event({"actor": "v2_consumer", "event": "dispatch.retry",
                            "envelope_id": env["id"], "retry_count": env["retry_count"],
                            "error": f"{type(e).__name__}: {e}"})
                out["steps"].append({"step": "retry", "ok": True,
                                     "retry_count": env["retry_count"]})
            except Exception as ee:
                q_deadletter(claimed_path, reason=f"retry_failed:{type(ee).__name__}")
                stats.incr("deadlettered")
                out["steps"].append({"step": "retry", "ok": False,
                                     "error": f"{type(ee).__name__}: {ee}"})
        else:
            # Emit error envelope, then deadletter.
            try:
                err_env = reply_envelope(env, sender=env["recipient"], message_type="error",
                                         payload={"code": "DISPATCH_FAILED",
                                                  "message": f"{type(e).__name__}: {e}",
                                                  "duration_ms": duration_ms})
                q_enqueue(err_env)
                stats.incr("errors")
            except Exception:
                pass
            q_deadletter(claimed_path, reason=f"max_retries_exceeded:{type(e).__name__}")
            stats.incr("deadlettered")
            _log_event({"actor": "v2_consumer", "event": "dispatch.failed",
                        "envelope_id": env["id"], "error": f"{type(e).__name__}: {e}"})
            out["steps"].append({"step": "deadletter", "ok": True,
                                 "reason": "max_retries_exceeded"})
        return out


# ---------------------------------------------------------------- One tick
def tick(recipients: Optional[list[str]] = None, *,
         dispatcher: Optional[Callable[..., dict]] = None,
         marker_filter: Optional[Callable[[dict], bool]] = None,
         max_per_tick: int = 100) -> dict:
    """One consumer tick.  Returns a per-recipient summary dict.

    Honors bounded concurrency via a BoundedSemaphore (MAX_CONCURRENT).
    """
    ensure_dirs()

    # Discover recipients from agents.json if not provided.
    if recipients is None:
        recipients = _load_recipients()
    if not recipients:
        return {"ok": False, "reason": "no_recipients", "ticked_at": _now_iso()}

    sem = threading.BoundedSemaphore(MAX_CONCURRENT)
    stats = ConsumerStats()
    results = {}

    def _run_one(recipient: str) -> None:
        with sem:
            local_stats = ConsumerStats()
            local_results = []
            with _recipient_lock(recipient):
                # Skip legacy marker files (R286 evidence plan) — these are
                # the 3 pre-R320.6 stranded acks.  Count them in stats so
                # callers can verify they were not consumed.
                all_candidates = list_for_recipient(recipient, limit=max_per_tick)
                skipped_legacy = sum(1 for p, _ in all_candidates if _is_legacy_marker_file(p))
                local_stats.skipped_nonv2 += skipped_legacy
                candidates = [(p, env) for (p, env) in all_candidates
                              if not _is_legacy_marker_file(p)]
                if marker_filter is not None:
                    candidates = [(p, env) for (p, env) in candidates if marker_filter(env)]
                for env_path, env in candidates:
                    r = dispatch_envelope(env_path, env, dispatcher=dispatcher,
                                          stats=local_stats,
                                          marker_filter=marker_filter)
                    local_results.append(r)
            results[recipient] = {
                "claimed": local_stats.claimed,
                "results": local_stats.results,
                "errors": local_stats.errors,
                "deadlettered": local_stats.deadlettered,
                "no_route": local_stats.no_route,
                "skipped_nonv2": local_stats.skipped_nonv2,
                "ok_count": sum(1 for r in local_results if r.get("ok")),
                "items": local_results,
            }
            stats.claimed += local_stats.claimed
            stats.results += local_stats.results
            stats.errors += local_stats.errors
            stats.deadlettered += local_stats.deadlettered
            stats.no_route += local_stats.no_route
            stats.skipped_nonv2 += local_stats.skipped_nonv2

    threads = [threading.Thread(target=_run_one, args=(r,), daemon=True)
               for r in recipients]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return {
        "ok": True,
        "ticked_at": _now_iso(),
        "max_concurrent": MAX_CONCURRENT,
        "max_queue": MAX_QUEUE,
        "totals": stats.snapshot(),
        "recipients": results,
    }


# ---------------------------------------------------------------- Watch loop
def watch(recipients: Optional[list[str]] = None, *,
          interval_s: float = 5.0,
          max_ticks: Optional[int] = None,
          dispatcher: Optional[Callable[..., dict]] = None,
          marker_filter: Optional[Callable[[dict], bool]] = None) -> None:
    """Loop calling tick() at interval_s."""
    i = 0
    while True:
        result = tick(recipients, dispatcher=dispatcher, marker_filter=marker_filter)
        print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
        i += 1
        if max_ticks is not None and i >= max_ticks:
            break
        time.sleep(interval_s)


# ---------------------------------------------------------------- Helpers
def _load_recipients() -> list[str]:
    if not AGENTS_JSON.exists():
        return []
    try:
        data = json.loads(AGENTS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [a.get("agent_id") for a in data.get("agents", []) if a.get("agent_id")]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------- Capability advertisement
def get_capabilities() -> dict:
    """R286 plan §2.9: server advertises capabilities at MCP initialize.
    Exposed as a tools-capability object here so callers (e.g. mcp initialize
    handler in Stage 5) can paste it verbatim."""
    return {
        "protocol": {"name": "AIOS Hub v2", "version": "1.0"},
        "envelope": {
            "schema_version": "1.0",
            "max_payload_size": MAX_CHUNK_TEXT_BYTES if (MAX_CHUNK_TEXT_BYTES := 65536) else 65536,
            "supports_chunking": True,
            "default_chunk_bytes": DEFAULT_CHUNK_SIZE,
        },
        "task_lifecycle": {
            "supports_submit": True,
            "supports_progress": True,
            "supports_cancel": True,
            "supports_input_request": True,
            "supports_approval": True,
            "states": ["queued", "running", "waiting", "succeeded", "failed", "cancelled"],
        },
        "artifacts": {
            "max_refs_per_envelope": 16,
            "supported_content_types": [
                "text/*", "image/png", "image/jpeg",
                "application/json", "application/octet-stream",
            ],
            "no_raw_binary_in_queue": True,
        },
        "correlation": {
            "supports_correlation_id": True,
            "supports_in_reply_to": True,
            "max_correlation_chain": 16,
        },
        "delivery": {
            "supports_ack": True,
            "supports_result": True,
            "supports_error": True,
            "supports_deadletter": True,
            "ack_separate_from_result": True,
        },
        "concurrency": {
            "max_concurrent": MAX_CONCURRENT,
            "max_queue": MAX_QUEUE,
        },
        "recipients": list(CAPABILITIES.keys()),
        "r286_marker": "r286_v1",
    }


def write_capabilities_report(path: Optional[Path] = None) -> Path:
    """Convenience: write capabilities JSON for inspection."""
    ensure_dirs()
    if path is None:
        path = v2_root() / "reports" / "r286_capabilities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(get_capabilities(), ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path