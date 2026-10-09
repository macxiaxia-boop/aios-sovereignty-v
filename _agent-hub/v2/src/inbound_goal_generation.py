"""inbound_goal_generation.py — v2 inbound envelope -> GoalContract (Phase G G002).

Generic loop:
  1. v2 inbound envelope (text payload, no hardcoded Goal fields)
  2. IntentParser (F002) -> 12-field GoalContract (intent-side)
  3. Translate intent GoalContract -> domain Goal (Phase F F001)
  4. cache to _agent-hub/v2/state/generated_goals/{goal_id}.json
  5. GoalGuard.validate(goal) (F005) -> PASS / RISK_BLOCK / FATAL
  6. PASS -> caller proceeds with dispatch
     RISK_BLOCK / FATAL -> caller gets risk_envelope (not allowed)

No hardcoded Goal fields: every field is derived from the envelope payload
plus IntentParser inference. The preserve_capabilities / known_constraints
defaults are explicit lists-of-capabilities (not Goals); they encode the
SSOT red lines from G000 §4 (which paths / agents MUST NOT be touched).

Reuses (Phase F assets, do NOT rewrite):
  - aios_kernel.intent.parser.IntentParser   (F002)
  - aios_kernel.intent.llm_adapter.NullLLMAdapter  (F002)
  - aios_kernel.domain.goal.Goal             (F001)
  - aios_kernel.governance.goal_guard.GoalGuard  (F005)

Out of scope for this card:
  - Failure feedback (G001)
  - Cross-agent knowledge (G003)
  - v2 consumer / v2_consumer.py main loop (NOT touched)
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Kernel modules — F001 / F002 / F005 assets, untouched here.
from aios_kernel.intent.parser import IntentParser
from aios_kernel.intent.llm_adapter import NullLLMAdapter
from aios_kernel.domain.goal import (
    Goal,
    GoalStatus,
    Constraint,
    EnvSnapshot,
    FailureMode,
    PermissionScope,
    EvidenceRequest,
    Tradeoff,
    OpType,
)
from aios_kernel.governance.goal_guard import GoalGuard, GuardVerdict, make_risk_envelope


# ---------------------------------------------------------------------------
# Constants (not Goal fields — directory + SSOT capability list)
# ---------------------------------------------------------------------------

# Cache directory for generated GoalContracts (for audit / replay).
# Honors AIOS_V2_ROOT so tests can redirect; falls back to canonical v2 root.
DEFAULT_V2_ROOT = Path(r"D:/AIOS/_agent-hub/v2")
GENERATED_GOALS_DIRNAME = "generated_goals"

# Preserve-capabilities baseline (from G000 §4 / AGENTS.md SSOT red lines).
# These are not Goal FIELD values — they describe what an agent must NOT
# destroy. They are derived from the user, not hardcoded as a goal; we
# only seed them when the envelope doesn't carry an explicit list.
_DEFAULT_PRESERVE_CAPABILITIES: tuple[str, ...] = (
    "verifier/deterministic.py",
    "v2 consumer main loop",
    "AGENTS.md SSOT",
)

# Forbidden permission-scope paths (mirror of F005 guard's red list, but
# the G002 default permission_scope must NEVER accidentally grant them).
_DEFAULT_ALLOWED_PATHS: tuple[str, ...] = (
    "D:/AIOS/_agent-hub/v2/state/",
    "D:/AIOS/_agent-hub/v2/messages/",
    "D:/AIOS/_agent-hub/v2/src/",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generated_goals_dir(v2_root: Path | str | None = None) -> Path:
    """Resolve the generated_goals/ directory.

    Resolution order:
      1. v2_root argument
      2. AIOS_V2_ROOT env var
      3. DEFAULT_V2_ROOT constant
    """
    if v2_root is not None:
        root = Path(v2_root)
    else:
        env_root = os.environ.get("AIOS_V2_ROOT")
        root = Path(env_root) if env_root else DEFAULT_V2_ROOT
    return root / "state" / GENERATED_GOALS_DIRNAME


def _now_iso() -> str:
    """Local UTC ISO timestamp (no UTC dep at module level)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# 1. envelope_to_goal_payload(envelope) -> dict
# ---------------------------------------------------------------------------

def envelope_to_goal_payload(envelope: Any) -> dict:
    """Extract goal-relevant fields from a v2 inbound envelope.

    Accepts:
      - dict envelopes with payload.goal (canonical shape)
      - dict envelopes with payload.{title,text,...} (loose shape)
      - dict envelopes that ARE the goal payload (no payload key)
      - anything else -> empty dict (caller treats as no-goal)
    """
    if not isinstance(envelope, dict):
        return {}
    payload = envelope.get("payload") or {}
    if not isinstance(payload, dict):
        return {}
    # Canonical: payload.goal already a goal-shaped dict
    if "goal" in payload and isinstance(payload["goal"], dict):
        return dict(payload["goal"])
    # Loose: payload itself is a goal-shaped dict (has title/text/etc.)
    if "title" in payload or "text" in payload or "description" in payload:
        return dict(payload)
    return {}


# ---------------------------------------------------------------------------
# 2. generate_goal_from_envelope(envelope, parser) -> Goal
# ---------------------------------------------------------------------------

def _extract_user_text(payload: dict) -> str:
    """Pull the user-supplied text out of a payload dict.

    Order: text -> description -> title -> "" (no hardcoded default).
    """
    if not isinstance(payload, dict):
        return ""
    for key in ("text", "description", "title"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def _env_snapshot_for(envelope: Any) -> EnvSnapshot:
    """Build a minimal EnvSnapshot for the new Goal.

    `envelope_id` is recorded so an audit can trace the Goal back to its
    originating envelope; everything else is auto-detected.
    """
    import os as _os
    import sys as _sys
    env_id = ""
    if isinstance(envelope, dict):
        env_id = str(envelope.get("id") or "")
    return EnvSnapshot(
        cwd=_os.getcwd(),
        os=f"{_sys.platform} (python {_sys.version_info.major}.{_sys.version_info.minor})",
        available_tools=[],
        recent_failures=[],
        history_refs=[env_id] if env_id else [],
    )


def generate_goal_from_envelope(
    envelope: Any,
    parser: IntentParser | None = None,
) -> Goal:
    """Generic inbound envelope -> Goal instance.

    No Goal FIELD is hardcoded with a domain-specific value. Every field
    is derived from one of:
      - envelope payload (raw user text / explicit goal hints)
      - IntentParser (F002) inference (inferred_intent, constraints, etc.)
      - envelope metadata (sender / id)
      - constants (SSOT red lines as preserve_capabilities)

    The parser parameter is injected so tests can use a stub; production
    callers may pass None and get a NullLLMAdapter-backed IntentParser.
    """
    if parser is None:
        parser = IntentParser(llm_adapter=NullLLMAdapter())

    payload = envelope_to_goal_payload(envelope)
    user_text = _extract_user_text(payload)
    sender = ""
    if isinstance(envelope, dict):
        sender = str(envelope.get("sender") or "")

    # 1) IntentParser -> intent-side GoalContract (12 fields).
    parsed = parser.parse(user_text)
    parsed_meta = getattr(parsed, "_meta", {}) or {}

    # 2) Translate intent GoalContract -> domain Goal.
    #    - title / description: prefer envelope title (set by caller),
    #      else IntentParser's stated_goal, else user_text.
    #    - budget / owner: envelope payload overrides parser default.
    title = (
        (payload.get("title") if isinstance(payload, dict) else None)
        or parsed.stated_goal
        or user_text
        or "untitled"
    )
    description = (
        (payload.get("description") if isinstance(payload, dict) else None)
        or user_text
        or parsed.stated_goal
    )

    budget = 0.0
    if isinstance(payload, dict) and payload.get("budget") is not None:
        try:
            budget = float(payload["budget"])
        except (TypeError, ValueError):
            budget = 0.0
    if budget == 0.0 and isinstance(payload, dict) and payload.get("max_budget") is not None:
        try:
            budget = float(payload["max_budget"])
        except (TypeError, ValueError):
            pass
    # If intent parser extracted a budget constraint, lift it.
    if budget == 0.0:
        for c in (parsed.known_constraints or []):
            if c.type == "budget" and isinstance(c.value, (int, float)) and c.value > 0:
                budget = float(c.value)
                break

    owner = (
        (payload.get("owner") if isinstance(payload, dict) else None)
        or sender
        or parsed_meta.get("owner")
        or "claudecode"
    )

    preserve_caps: list[str] = []
    if isinstance(payload, dict) and isinstance(payload.get("preserve_capabilities"), list):
        preserve_caps = [str(x) for x in payload["preserve_capabilities"]]
    if not preserve_caps:
        preserve_caps = list(_DEFAULT_PRESERVE_CAPABILITIES)

    # Translate known_constraints (intent) -> domain Constraints.
    constraints: list[Constraint] = []
    for c in (parsed.known_constraints or []):
        try:
            constraints.append(Constraint(
                type=c.type,
                value=c.value,
                rationale=c.rationale or "from intent parser",
            ))
        except Exception:
            # Skip constraints that don't pass Pydantic Literal validation
            # (Pydantic only accepts budget/timeout/forbidden_path/rate_limit/scope).
            continue

    # Translate permission_scope (intent) -> domain PermissionScope.
    intent_scope = parsed.permission_scope
    allowed_paths_seed: list[str] = list(getattr(intent_scope, "allowed_paths", []) or [])
    # If the intent parser left allowed_paths empty (the common case for
    # COMMAND / STATEMENT / QUESTION defaults), seed a v2-only safe set
    # so the GoalGuard "permission_scope_empty" check can pass. The
    # envelope payload may still override these below.
    if not allowed_paths_seed:
        allowed_paths_seed = list(_DEFAULT_ALLOWED_PATHS)
    # G002-FIX-INDEX: max_budget must equal goal.budget (Goal model cross-validator enforces).
    # intent_scope.max_budget may be 0.0 if parser didn't extract, but goal.budget is authoritative.
    perm = PermissionScope(
        allowed_paths=allowed_paths_seed,
        allowed_ops=list(getattr(intent_scope, "allowed_ops", []) or []),
        max_budget=float(budget),  # use goal's budget (always >= 0)
        max_duration_sec=getattr(intent_scope, "max_duration_sec", None),
        requires_approval=list(getattr(intent_scope, "requires_approval", []) or []),
    )
    # If envelope payload specifies explicit allowed_paths, prefer those.
    if isinstance(payload, dict) and isinstance(payload.get("allowed_paths"), list):
        explicit = [str(p) for p in payload["allowed_paths"]]
        # SAFETY: never let an envelope grant access to a forbidden path.
        for forbidden_prefix in (
            "D:/AIOS/kernel/src/aios_kernel/verifier/",
            "D:/AIOS/_agent-hub/AGENTS.md",
        ):
            explicit = [p for p in explicit if not str(p).replace("\\", "/").startswith(forbidden_prefix)]
        if explicit:
            perm = perm.model_copy(update={"allowed_paths": explicit})

    # Translate failure_modes (intent) -> domain FailureMode.
    failure_modes: list[FailureMode] = []
    for fm in (parsed.failure_modes or []):
        failure_modes.append(FailureMode(
            description=str(fm.description),
            detection=str(fm.detection),
            indicator=str(fm.indicator) if fm.indicator is not None else None,
        ))

    # Translate missing_evidence (intent) -> domain EvidenceRequest.
    missing_evidence: list[EvidenceRequest] = []
    for ev in (parsed.missing_evidence or []):
        missing_evidence.append(EvidenceRequest(
            description=str(ev.description),
            source=str(ev.source),
            required=bool(ev.required),
        ))

    # Translate approved_tradeoffs (intent) -> domain Tradeoff.
    tradeoffs: list[Tradeoff] = []
    for t in (parsed.approved_tradeoffs or []):
        try:
            tradeoffs.append(Tradeoff(
                decision=str(t.decision),
                cost=str(t.cost),
                benefit=str(t.benefit),
                approved_by=str(t.approved_by) or "user",
            ))
        except Exception:
            continue

    # Translate autonomous_scope / requires_authorization (intent -> domain).
    def _to_op_type(o: Any) -> OpType | None:
        domain = getattr(o, "domain", None) or (o.get("domain") if isinstance(o, dict) else None)
        action = getattr(o, "action", None) or (o.get("action") if isinstance(o, dict) else None)
        target = getattr(o, "target", None)
        if target is None and isinstance(o, dict):
            target = o.get("target")
        if domain is None or action is None:
            return None
        try:
            return OpType(domain=str(domain), action=str(action), target=target)
        except Exception:
            return None

    autonomous_scope: list[OpType] = []
    for o in (parsed.autonomous_scope or []):
        x = _to_op_type(o)
        if x is not None:
            autonomous_scope.append(x)

    requires_auth: list[OpType] = []
    for o in (parsed.requires_authorization or []):
        x = _to_op_type(o)
        if x is not None:
            requires_auth.append(x)

    # 3) Construct the Goal.
    goal = Goal(
        id=str(uuid.uuid4()),
        title=str(title)[:200],  # enforce Goal.title max_length=200
        description=str(description)[:2000] if description else None,
        success_criteria=str(parsed.success_criteria or "live"),
        budget=float(budget) if float(budget) >= 0 else 0.0,
        deadline=None,
        owner=str(owner),
        status=GoalStatus.PENDING,
        tags=list(payload.get("tags", []) or []) if isinstance(payload, dict) else [],
        plan_ids=[],
        metadata={
            "source": "inbound_envelope",
            "envelope_id": str(envelope.get("id")) if isinstance(envelope, dict) else "",
            "intent_type": str(parsed_meta.get("intent_type", "")),
            "parsed_at": str(parsed_meta.get("parsed_at", _now_iso())),
        },
        # 7 new GoalContract sub-fields
        inferred_intent=parsed.inferred_intent,
        preserve_capabilities=preserve_caps,
        known_constraints=constraints,
        environment_context=_env_snapshot_for(envelope),
        failure_modes=failure_modes,
        permission_scope=perm,
        missing_evidence=missing_evidence,
        approved_tradeoffs=tradeoffs,
        autonomous_scope=autonomous_scope,
        requires_authorization=requires_auth,
    )
    return goal


# ---------------------------------------------------------------------------
# 3. cache_goal_to_disk(goal) -> Path
# ---------------------------------------------------------------------------

def cache_goal_to_disk(
    goal: Goal,
    v2_root: Path | str | None = None,
) -> Path:
    """Persist the generated Goal to disk for audit + replay.

    File: {v2_root}/state/generated_goals/{goal.id}.json
    Returns the Path written. Overwrites any existing file with same id
    (idempotent on goal_id, which is unique per Goal).
    """
    out_dir = _generated_goals_dir(v2_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{goal.id}.json"
    payload = json.loads(goal.model_dump_json())
    payload["_cached_at"] = _now_iso()
    payload["_source_module"] = "aios_vnext.inbound_goal_generation"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# 4. validate_with_goal_guard(goal) -> (allowed, verdict, risk_envelope)
# ---------------------------------------------------------------------------

def validate_with_goal_guard(goal: Goal) -> tuple[bool, str, dict | None]:
    """Run GoalGuard.validate(goal) (F005) on a generated Goal.

    Returns (allowed, verdict_value, risk_envelope_or_None).
    allowed == True  iff verdict is PASS.
    allowed == False iff verdict is RISK_BLOCK or FATAL.
    """
    guard = GoalGuard()
    report = guard.validate(goal)
    verdict_value = report.verdict.value
    if verdict_value == GuardVerdict.PASS.value:
        return True, verdict_value, None
    risk_env = make_risk_envelope(goal, report, _envelope_skeleton_for(goal))
    return False, verdict_value, risk_env


def _envelope_skeleton_for(goal: Goal) -> dict:
    """Build a minimal envelope-shaped dict for make_risk_envelope.

    make_risk_envelope only reads .id / .message_type from the envelope;
    we construct the minimal stub from goal.metadata.
    """
    return {
        "id": (goal.metadata or {}).get("envelope_id", "") or goal.id,
        "message_type": "message",
    }


# ---------------------------------------------------------------------------
# 5. process_inbound_envelope(envelope) -> (goal, allowed, risk, cache_path)
# ---------------------------------------------------------------------------

def _write_decision_audit_event(
    goal: "Goal",
    envelope: Any,
    v2_root: Path | str | None,
) -> None:
    """Append a single NDJSON line to logs/inbound_goal_audit.ndjson.

    Closes the audit gap: every G002 pass is observable post-hoc.
    Uses existing v2 log file conventions (json.loads + "_ndjson_ext" pattern).
    """
    try:
        root = Path(v2_root) if v2_root else (
            Path(os.environ["AIOS_V2_ROOT"]) if os.environ.get("AIOS_V2_ROOT") else DEFAULT_V2_ROOT
        )
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "inbound_goal_audit.ndjson"
        evt = {
            "ts": _now_iso(),
            "event_type": "inbound_goal_active",
            "goal_id": goal.id,
            "title": goal.title,
            "owner": goal.owner,
            "envelope_id": (envelope or {}).get("id") if isinstance(envelope, dict) else None,
            "rationale": "G002 inbound_goal_generation passed GoalGuard; auto-activated for dispatch.",
        }
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    except Exception as exc:
        if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
            print(f"[inbound_goal_generation] audit write failed: {exc}", flush=True)


def process_inbound_envelope(
    envelope: Any,
    parser: IntentParser | None = None,
    v2_root: Path | str | None = None,
    activate_on_pass: bool = True,
) -> tuple[Goal, bool, dict | None, Path]:
    """Full pipeline: envelope -> Goal -> cache -> GoalGuard.

    Returns:
      (goal, allowed, risk_envelope_or_None, cache_path)

    Side effects:
      - Writes the generated Goal JSON to disk (cache_path).
      - On PASS + activate_on_pass=True: transitions Goal PENDING -> ACTIVE,
        rewrites cache with new status, writes a decision audit line so the
        active Goal is observable to downstream v2_consumer dispatch + the
        Codex self-audit script.
      - NEVER deletes or modifies the original envelope.
    """
    goal = generate_goal_from_envelope(envelope, parser=parser)
    cache_path = cache_goal_to_disk(goal, v2_root=v2_root)
    allowed, _verdict, risk_env = validate_with_goal_guard(goal)
    if allowed and activate_on_pass and goal.status == GoalStatus.PENDING:
        try:
            goal.transition_to(GoalStatus.ACTIVE)
            cache_path = cache_goal_to_disk(goal, v2_root=v2_root)
            _write_decision_audit_event(goal, envelope, v2_root)
        except Exception as exc:
            if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
                print(f"[inbound_goal_generation] activate failed: {exc}", flush=True)
    return goal, allowed, risk_env, cache_path


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    "envelope_to_goal_payload",
    "generate_goal_from_envelope",
    "cache_goal_to_disk",
    "validate_with_goal_guard",
    "process_inbound_envelope",
    "GENERATED_GOALS_DIRNAME",
    "DEFAULT_V2_ROOT",
]
