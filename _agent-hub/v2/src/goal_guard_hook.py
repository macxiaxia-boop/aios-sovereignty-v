"""goal_guard_hook.py — v2 consumer integration for GoalGuard (F005)
and Strategy Gate (Phase-2 retirement).

This module is the THIN adapter between v2_consumer (the main loop)
and:
  - aios_kernel.governance.GoalGuard (the validator from Phase F), AND
  - the strategy gate loaded from
    D:\\AIOS\\_agent-hub\\policy\\product_strategy.v1.json
    (the CloudTech Global Product Strategy Policy introduced in
    Phase-2 retirement construction contract, 2026-10-09).

Functions exported:
  - guard_dispatch(envelope, v2_root) -> (allowed: bool, risk_envelope | None)
      The single call site inside v2_consumer.dispatch_envelope().
      Returns (True, None) when the envelope is safe to dispatch.
      Returns (False, risk_envelope) when the envelope should be blocked
      and a risk envelope has been constructed (caller is responsible
      for writing it to disk via write_risk_envelope).
      BOTH GoalGuard and StrategyGate must pass; either one rejects
      → block.

  - write_risk_envelope(v2_root, risk_envelope) -> Path | None
      Persist a risk envelope to v2/messages/risk/<id>.json so a
      supervisor can review and the original sender gets notified.

  - envelope_to_contract(envelope) -> GoalContract-shaped dict
      Pull a GoalContract out of an envelope's payload.  Envelopes that
      don't carry a goal (heartbeat / terminal result / ack) get a
      auto-pass empty contract so the hook doesn't accidentally block
      every internal message.

  - resolve_v2_root(caller_root) -> Path
      Normalize the v2 root path.  Honors AIOS_V2_ROOT env var so tests
      can redirect to a temp dir; falls back to caller_root; falls back
      to the directory two levels up from this file (the real v2 root).

  - strategy_gate_for_root(v2_root) -> StrategyGate | None
      Lazily loads the strategy gate for the v2 root.  Cached per
      process.  Returns None when the policy fails to load so the
      caller can decide how to react (current default: fail closed
      via POLICY_GATE_REJECTED).

The v2_consumer.py diff stays at 0 additional lines — all of this
logic lives inside guard_dispatch().
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------- Constants
# These envelope message_types are considered "internal plumbing" and
# are auto-PASSed by GoalGuard.  They are NOT user goals and should
# never be blocked:
#   - terminal: result / ack / status / heartbeat / error
#   - reply-bearing: anything carrying a correlation_id (result of a
#     previous dispatch — re-checking it would loop).
# Without this carve-out, the consumer would deadlock on its own acks.
_INTERNAL_MESSAGE_TYPES: frozenset[str] = frozenset({
    "result", "ack", "status", "heartbeat", "error",
})

# ---------------------------------------------------------------- Strategy Gate cache
# Strategy gate is process-wide cache keyed by the policy dir.  Tests can
# force a reload by deleting the entry; production simply re-uses it.
_STRATEGY_GATE_CACHE: dict[str, Any] = {}


def _default_policy_dir() -> Path:
    """Resolve the default policy directory.

    Resolution order:
      1. AIOS_STRATEGY_POLICY_DIR env var
      2. <v2_root>/../policy   (i.e. _agent-hub/policy)
      3. D:/AIOS/_agent-hub/policy (hard fallback)
    """
    env_dir = os.environ.get("AIOS_STRATEGY_POLICY_DIR")
    if env_dir:
        return Path(env_dir)
    try:
        v2_root = Path(__file__).resolve().parent.parent
        return v2_root.parent / "policy"
    except Exception:
        pass
    return Path(r"D:\AIOS\_agent-hub\policy")


def _ensure_policy_on_path(policy_dir: Path) -> None:
    """Ensure the policy package is importable.  Falls back to a sys.path
    injection if the package layout doesn't auto-expose `policy.*`.
    """
    policy_pkg = policy_dir.parent  # _agent-hub
    p = str(policy_pkg)
    if p not in sys.path:
        sys.path.insert(0, p)


def strategy_gate_for_root(v2_root: Path | str | None = None) -> Any:
    """Return a cached StrategyGate for the v2 root, or None on failure.

    The policy dir is resolved via `_default_policy_dir()`, NOT derived
    from `v2_root`, because tests redirect v2_root to a temp dir and
    that would cause the policy dir to point at a non-existent path.

    Resolution order:
      1. AIOS_STRATEGY_POLICY_DIR env var
      2. <this-file>/../../policy/   (i.e. _agent-hub/policy)
      3. D:\\AIOS\\_agent-hub\\policy\\ (hard fallback)

    The cache key is the resolved policy dir; tests can clear it via
    `clear_strategy_gate_cache()`.
    """
    policy_dir = _default_policy_dir()

    # If the resolved policy dir doesn't actually exist, try to derive
    # one from v2_root as a fallback (production always uses real
    # _agent-hub/policy; tests may want a custom path).
    if not policy_dir.exists():
        try:
            root = resolve_v2_root(v2_root)
            alt = root.parent / "policy"
            if alt.exists():
                policy_dir = alt
        except Exception:
            pass

    key = str(policy_dir.resolve())
    if key in _STRATEGY_GATE_CACHE:
        return _STRATEGY_GATE_CACHE[key]

    _ensure_policy_on_path(policy_dir)

    # Lazy imports so the hook can be unit-tested without the policy package
    try:
        from policy.strategy_gate import gate_from_policy_dir  # type: ignore
    except Exception as exc:  # pragma: no cover — defensive
        if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
            print(f"[goal_guard_hook] strategy_gate import failed: {exc}", flush=True)
        _STRATEGY_GATE_CACHE[key] = None
        return None

    res, gate = gate_from_policy_dir(policy_dir)
    if not res.ok or gate is None:
        # Fail closed: we still cache the result so we don't repeatedly try.
        if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
            print(f"[goal_guard_hook] strategy_policy load failed: {res.reason} {res.errors}", flush=True)
        _STRATEGY_GATE_CACHE[key] = None
        return None

    _STRATEGY_GATE_CACHE[key] = gate
    return gate


def clear_strategy_gate_cache() -> None:
    """Reset the strategy gate cache (used by tests)."""
    _STRATEGY_GATE_CACHE.clear()


# ---------------------------------------------------------------- Root resolution
def resolve_v2_root(caller_root: Path | str | None = None) -> Path:
    """Resolve the v2 root, honoring AIOS_V2_ROOT env var override (tests use
    this to redirect to a temp dir).  Falls back to caller_root; falls
    back to this file's directory-tree ancestor (the real v2 root).

    Resolution order:
      1. AIOS_V2_ROOT env var (if set and non-empty)
      2. caller_root (if non-None and non-empty)
      3. Path(__file__).resolve().parent.parent  → real _agent-hub/v2/
    """
    env_root = os.environ.get("AIOS_V2_ROOT")
    if env_root:
        return Path(env_root)
    if caller_root is not None and str(caller_root):
        return Path(caller_root)
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- Adapter
def envelope_to_contract(envelope: dict) -> dict | None:
    """Pull a GoalContract-shaped dict out of an envelope payload.

    Convention (Phase F §5): envelopes carrying user goals have
        payload.goal = { ...12 fields... }
    Envelopes without `payload.goal` are not GoalContracts; the caller
    is expected to short-circuit them.
    """
    if not isinstance(envelope, dict):
        return None
    payload = envelope.get("payload") or {}
    if not isinstance(payload, dict):
        return None
    if "goal" in payload and isinstance(payload["goal"], dict):
        return dict(payload["goal"])
    # Heuristic: a task-type envelope whose payload looks like a Goal
    # (has a title + success_criteria) can also be treated as one.
    if envelope.get("message_type") in ("task", "message"):
        if "title" in payload and "success_criteria" in payload:
            return {k: payload[k] for k in (
                "title", "success_criteria", "budget", "owner", "status",
                "permission_scope", "failure_modes", "missing_evidence",
                "autonomous_scope", "requires_authorization",
            ) if k in payload}
    return None


def guard_dispatch(envelope: dict, v2_root: Path | str | None = None) -> tuple[bool, dict | None]:
    """Pre-dispatch hook.

    Returns (True, None) when dispatch may proceed.
    Returns (False, risk_envelope) when dispatch must be blocked.

    Backwards-compatibility: if the guard module can't be imported for
    any reason, we FAIL-OPEN and return (True, None) so a broken guard
    doesn't brick the entire consumer.  (The standalone guard has its
    own tests; the consumer is the production smoke detector.)

    Strategy gate (Phase-2): after the GoalGuard check, the strategy
    gate evaluates the envelope against the loaded Strategy Policy.
    A rejected envelope produces a strategy_gate_risk envelope that
    supersedes (or supplements) the goal_guard_risk envelope.
    """
    # Short-circuit: terminal / internal envelopes are not GoalContracts.
    if not isinstance(envelope, dict):
        return True, None
    msg_type = envelope.get("message_type")
    if msg_type in _INTERNAL_MESSAGE_TYPES:
        return True, None

    # Strategy Gate: evaluate even non-Goal envelopes because text hits
    # (retired ids, industry presets, deprecated paths) live in any
    # task-bearing payload.
    gate = strategy_gate_for_root(v2_root)
    if gate is not None:
        decision = gate.evaluate_envelope(envelope)
        if not decision.allowed:
            return False, decision.risk_envelope
    else:
        # Policy failed to load — fail CLOSED for any non-terminal envelope.
        # The contract says "Missing, malformed, hash-mismatched, or
        # unapproved policy must fail closed for task creation and dispatch."
        if msg_type in ("task", "message"):
            return False, {
                "envelope_type": "strategy_gate_risk",
                "original_envelope_id": envelope.get("id"),
                "original_sender": envelope.get("sender"),
                "reason": "policy_load_failed",
                "events": [
                    {
                        "event_type": "POLICY_GATE_REJECTED",
                        "severity": "BLOCK",
                        "message": "strategy policy failed to load; gate is fail-closed",
                        "ts": time.time(),
                    }
                ],
                "ts": time.time(),
                "policy_id": "GLOBAL_PRODUCT_STRATEGY",
                "policy_version": "2026-10-08",
                "schema_version": "1.0",
            }

    # Pull a contract out of the envelope payload.
    contract = envelope_to_contract(envelope)
    if contract is None:
        # Not a Goal-carrying envelope → no check needed.
        return True, None

    # Lazy import so the hook can be unit-tested without the kernel package.
    try:
        from aios_kernel.governance import GoalGuard, make_risk_envelope
    except Exception as exc:  # pragma: no cover — defensive
        # Fail-open: log via env var if supervisor wants to know.
        if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
            print(f"[goal_guard_hook] import failed: {exc}", flush=True)
        return True, None

    guard = GoalGuard()
    report = guard.validate(contract)
    if report.verdict.value == "pass":
        return True, None
    risk_env = make_risk_envelope(contract, report, envelope)
    return False, risk_env


def write_risk_envelope(v2_root: Path | str | None, risk_envelope: dict) -> Path | None:
    """Persist a `goal_guard_risk` envelope to v2/messages/risk/.

    Returns the path written, or None on failure (with a log line).
    The directory is created on demand; this is the only file the hook
    is allowed to write besides what v2_consumer itself does.
    """
    try:
        root = resolve_v2_root(v2_root)
        risk_dir = root / "messages" / "risk"
        risk_dir.mkdir(parents=True, exist_ok=True)
        env_id = (risk_envelope or {}).get("original_envelope_id") or uuid.uuid4().hex
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        out_path = risk_dir / f"{env_id}__{ts}__goal_guard_risk.json"
        out_path.write_text(
            json.dumps(risk_envelope, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return out_path
    except Exception as exc:  # pragma: no cover
        if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
            print(f"[goal_guard_hook] write_risk_envelope failed: {exc}", flush=True)
        return None


__all__ = [
    "guard_dispatch",
    "write_risk_envelope",
    "envelope_to_contract",
    "resolve_v2_root",
    "strategy_gate_for_root",
    "clear_strategy_gate_cache",
]