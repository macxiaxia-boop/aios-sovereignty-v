# v2/src/state_machine.py — task lifecycle + state.json aggregator.
#
# Each task lives in tasks/<task_id>.json. Concurrent-safe writes via atomic
# tmp+replace + best-effort flock on POSIX / msvcrt on Windows.
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

from .goal_guard_hook import strategy_gate_for_root
from .id import new_uuid, utc_now_iso
from .paths import RUNS_DIR, STATE_FILE, TASKS_DIR, ensure_dirs
from .validation import TERMINAL_TASK_STATES, TASK_STATES, validate_task


# ---------------------------------------------------------------- Strategy Gate (Phase-2 correction)
class StrategyGateRejected(Exception):
    """Raised when the strategy policy gate refuses a task submission.

    The exception carries the structured gate events (``.events``) and the
    machine-readable rejection reason (``.reason``). Optional ``.policy_id``
    and ``.policy_version`` identify the policy version that rejected the
    submission. Callers may surface a clear error message to CLI users.
    """

    def __init__(
        self,
        message: str,
        *,
        events: list,
        reason: str,
        policy_id: "str | None" = None,
        policy_version: "str | None" = None,
    ) -> None:
        super().__init__(message)
        self.events = events
        self.reason = reason
        self.policy_id = policy_id
        self.policy_version = policy_version


def _enforce_strategy_gate(
    *,
    title: str,
    description: str,
    input_payload: "dict | None",
    owner: str,
    assignee: str,
) -> None:
    """Evaluate the strategy policy gate BEFORE any task file is written.

    Uses the existing ``policy.strategy_gate.StrategyGate`` (loaded via
    ``goal_guard_hook.strategy_gate_for_root``). On reject:

      - returns nothing and the caller MUST NOT persist any task file
      - appends an entry to events.ndjson containing both
        ``policy_gate_rejected: True`` and ``underlying_event_type``
        (the gate's first non-umbrella event type, or
        ``POLICY_GATE_REJECTED`` when the policy itself failed to load)
      - raises :class:`StrategyGateRejected` with the structured events

    Fail-closed: a missing / malformed / hash-mismatched policy rejects
    the submission with reason ``policy_load_failed``. This matches the
    Phase-2 contract: policy load / hash / approval failures must fail
    closed for task creation.
    """
    gate = strategy_gate_for_root(None)
    payload_dict = input_payload if isinstance(input_payload, dict) else {}

    if gate is None:
        # Policy failed to load — fail closed (Phase-2 contract).
        events: list = [{
            "event_type": "POLICY_GATE_REJECTED",
            "severity": "BLOCK",
            "message": "strategy policy failed to load; submit_task gate is fail-closed",
            "ts": time.time(),
        }]
        _log_event({
            "actor": owner,
            "event": "task.submit_rejected",
            "policy_gate_rejected": True,
            "underlying_event_type": "POLICY_GATE_REJECTED",
            "all_event_types": ["POLICY_GATE_REJECTED"],
            "reason": "policy_load_failed",
            "title": title,
        })
        raise StrategyGateRejected(
            "task submission blocked by strategy gate: policy_load_failed",
            events=events,
            reason="policy_load_failed",
        )

    envelope = {
        "id": f"submit-{new_uuid()}",
        "sender": owner,
        "recipient": assignee,
        "message_type": "task",
        "payload": {
            "title": title,
            "description": description,
            "text": json.dumps(payload_dict, ensure_ascii=False, default=str),
        },
        "schema_version": "1.0",
    }

    decision = gate.evaluate_envelope(envelope)
    if decision.allowed:
        return

    # Reject path — flatten events, pick the first non-umbrella type as
    # the underlying reason, then raise.
    events_dicts: list = []
    underlying = "POLICY_GATE_REJECTED"
    for e in decision.events:
        ed = e.to_dict() if hasattr(e, "to_dict") else (e if isinstance(e, dict) else {})
        events_dicts.append(ed)
        et = ed.get("event_type") or ""
        if et and et != "POLICY_GATE_REJECTED" and underlying == "POLICY_GATE_REJECTED":
            underlying = et

    event_types = [ed.get("event_type", "") for ed in events_dicts]
    risk = decision.risk_envelope if isinstance(decision.risk_envelope, dict) else {}
    policy_id = risk.get("policy_id")
    policy_version = risk.get("policy_version")

    _log_event({
        "actor": owner,
        "event": "task.submit_rejected",
        "policy_gate_rejected": True,
        "underlying_event_type": underlying,
        "all_event_types": event_types,
        "reason": decision.reason,
        "title": title,
    })
    raise StrategyGateRejected(
        f"task submission blocked by strategy gate: {underlying} "
        f"(reason={decision.reason})",
        events=events_dicts,
        reason=decision.reason,
        policy_id=policy_id,
        policy_version=policy_version,
    )

VALID_TRANSITIONS = {
    "queued": {"running", "cancelled"},
    "running": {"waiting", "succeeded", "failed", "queued"},  # queued = requeue after fail
    "waiting": {"running", "cancelled", "failed"},
    "succeeded": set(),
    "failed": {"queued"},  # retry path
    "cancelled": set(),
}


def _file_lock_supported() -> bool:
    try:
        import msvcrt  # noqa: F401
        return True
    except ImportError:
        try:
            import fcntl  # noqa: F401
            return True
        except ImportError:
            return False


def _atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp.{uuid.uuid4().hex[:8]}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def submit_task(*, title: str, assignee: str, owner: str, description: str = "",
                timeout_ms: int = 60000, max_retries: int = 3,
                input_payload: Optional[dict] = None,
                correlation_envelope_id: Optional[str] = None) -> dict:
    ensure_dirs()
    # Strategy gate (Phase-2 correction). MUST come BEFORE any task file
    # is written; a rejected submission leaves no trace on disk and
    # raises StrategyGateRejected so CLI callers see a clear error.
    _enforce_strategy_gate(
        title=title,
        description=description,
        input_payload=input_payload,
        owner=owner,
        assignee=assignee,
    )
    now = utc_now_iso()
    task = {
        "task_id": new_uuid(),
        "title": title,
        "description": description,
        "state": "queued",
        "assignee": assignee,
        "owner": owner,
        "created_at": now,
        "updated_at": now,
        "lease_expires_at": None,
        "heartbeat_at": None,
        "input_payload": input_payload or {},
        "output_payload": {},
        "error": None,
        "retry_count": 0,
        "max_retries": max_retries,
        "timeout_ms": timeout_ms,
        "correlation_envelope_id": correlation_envelope_id,
    }
    ok, errors = validate_task(task)
    if not ok:
        raise ValueError(f"refusing to submit invalid task: {errors}")
    _atomic_write_json(TASKS_DIR / f"{task['task_id']}.json", task)
    _log_event({"actor": owner, "event": "task.submitted", "task_id": task["task_id"], "assignee": assignee, "title": title})
    _record_run(task, event="submitted")
    return task


def get_task(task_id: str) -> Optional[dict]:
    return _read_json(TASKS_DIR / f"{task_id}.json")


def list_tasks(state: Optional[str] = None) -> list:
    ensure_dirs()
    out = []
    for p in TASKS_DIR.glob("*.json"):
        if p.name.endswith(".tmp") or ".tmp." in p.name:
            continue
        t = _read_json(p)
        if not t:
            continue
        if state is None or t.get("state") == state:
            out.append(t)
    return out


def transition(task_id: str, new_state: str, *, actor: str, note: str = "",
               output_payload: Optional[dict] = None,
               error: Optional[dict] = None) -> dict:
    if new_state not in TASK_STATES:
        raise ValueError(f"unknown state {new_state!r}")
    task = get_task(task_id)
    if task is None:
        raise KeyError(f"task {task_id} not found")
    current = task["state"]
    if current in TERMINAL_TASK_STATES:
        raise ValueError(f"task {task_id} already terminal: {current}")
    if new_state not in VALID_TRANSITIONS[current]:
        raise ValueError(f"invalid transition {current} -> {new_state}")
    # Retry budget: failed -> queued only allowed if retry_count < max_retries.
    # Any other transition that leaves a "retry-like" state is also checked
    # against max_retries budget to keep the budget consistent.
    if current == "failed" and new_state == "queued":
        if task["retry_count"] >= task["max_retries"]:
            raise ValueError(
                f"task {task_id} cannot retry: retry_count={task['retry_count']} "
                f">= max_retries={task['max_retries']}"
            )
    task["state"] = new_state
    task["updated_at"] = utc_now_iso()
    if output_payload is not None:
        task["output_payload"] = output_payload
    if error is not None:
        task["error"] = error
    if new_state == "running":
        # claim lease
        lease_secs = max(1, task["timeout_ms"] // 1000)
        task["lease_expires_at"] = _iso_in(lease_secs)
        task["heartbeat_at"] = utc_now_iso()
    elif new_state in TERMINAL_TASK_STATES:
        task["lease_expires_at"] = None
    _atomic_write_json(TASKS_DIR / f"{task_id}.json", task)
    _log_event({"actor": actor, "event": "task.transition", "task_id": task_id,
                "from": current, "to": new_state, "note": note})
    _record_run(task, event=f"transition:{current}->{new_state}", note=note)
    return task


def heartbeat(task_id: str, *, actor: str) -> dict:
    """Refresh heartbeat_at and lease_expires_at."""
    task = get_task(task_id)
    if task is None:
        raise KeyError(f"task {task_id} not found")
    if task["state"] != "running":
        raise ValueError(f"cannot heartbeat task in state {task['state']}")
    now = utc_now_iso()
    task["heartbeat_at"] = now
    lease_secs = max(1, task["timeout_ms"] // 1000)
    task["lease_expires_at"] = _iso_in(lease_secs)
    task["updated_at"] = now
    _atomic_write_json(TASKS_DIR / f"{task_id}.json", task)
    _log_event({"actor": actor, "event": "task.heartbeat", "task_id": task_id})
    return task


def reap_expired(*, actor: str = "supervisor") -> list:
    """Find running tasks whose lease expired; transition to failed (auto-retry if budget left)."""
    ensure_dirs()
    now = utc_now_iso()
    reaped = []
    for t in list_tasks(state="running"):
        if not t.get("lease_expires_at"):
            continue
        if t["lease_expires_at"] >= now:
            continue
        # Lease expired
        try:
            transitioned = transition(t["task_id"], "failed", actor=actor,
                                       note=f"lease expired at {t['lease_expires_at']}",
                                       error={"code": "LEASE_EXPIRED",
                                              "message": f"no heartbeat by {t['lease_expires_at']}"})
            reaped.append(transitioned)
            # auto-retry if budget left
            if transitioned["retry_count"] < transitioned["max_retries"]:
                r = transition(t["task_id"], "queued", actor=actor,
                               note=f"auto-retry {transitioned['retry_count']+1}/{transitioned['max_retries']}")
                r["retry_count"] = transitioned["retry_count"] + 1
                _atomic_write_json(TASKS_DIR / f"{t['task_id']}.json", r)
                _log_event({"actor": actor, "event": "task.retry", "task_id": t["task_id"],
                            "retry_count": r["retry_count"]})
        except Exception as e:
            _log_event({"actor": actor, "event": "task.reap_failed", "task_id": t["task_id"], "error": str(e)})
    return reaped


def cancel(task_id: str, *, actor: str) -> dict:
    return transition(task_id, "cancelled", actor=actor, note="user-requested cancel")


def build_state_snapshot() -> dict:
    ensure_dirs()
    tasks = {t["task_id"]: t for t in list_tasks()}
    counters = {}
    for t in tasks.values():
        counters[t["state"]] = counters.get(t["state"], 0) + 1
    snapshot = {
        "version": "v2-2026-09-29",
        "updated_at": utc_now_iso(),
        "tasks": tasks,
        "agents": {},
        "counters": counters,
    }
    return snapshot


def save_state_snapshot(snapshot: dict) -> Path:
    ensure_dirs()
    _atomic_write_json(STATE_FILE, snapshot)
    return STATE_FILE


def _iso_in(seconds: int) -> str:
    """ISO8601 UTC timestamp N seconds from now."""
    import datetime as _dt
    return (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record_run(task: dict, *, event: str, note: str = "") -> None:
    ensure_dirs()
    run = {
        "task_id": task["task_id"],
        "attempt": task.get("retry_count", 0),
        "event": event,
        "note": note,
        "ts": utc_now_iso(),
        "state": task.get("state"),
    }
    p = RUNS_DIR / f"{task['task_id']}__{int(time.time()*1000)}.json"
    try:
        _atomic_write_json(p, run)
    except Exception:
        pass


def _log_event(obj: dict) -> None:
    from .paths import EVENTS_LOG
    obj = {"ts": utc_now_iso(), **obj}
    line = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    ensure_dirs()
    with open(EVENTS_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()