"""goal_guard.py — GoalContract validation guard (F005 / Phase F).

v2 consumer calls GoalGuard.validate(contract_or_dict) before dispatching
any envelope.  The guard enforces the GoalContract 12-field schema from
F000 spec §2 and returns one of three verdicts:

  - PASS       → dispatch as normal
  - RISK_BLOCK → write a `goal_guard_risk` envelope to v2/messages/risk/
                  and SKIP the dispatch (the original envelope is left
                  unclaimed so a human can re-queue after fixing).
  - FATAL      → guard isolates the envelope (permission overrun); the
                  caller should dead-letter with reason
                  `goal_guard_fatal:<details>` and never retry.

Design choices
--------------
1. The guard never imports from the existing `Goal` Pydantic model
   directly.  F001 is responsible for the 12-field schema; until F001
   merges, the guard uses its OWN `GoalContract` dataclass + duck-typed
   readers via `getattr(...)`.  This means F005 works independently of
   F001 and survives the F001 merge unchanged.

2. The 5 checks are implemented as small private helpers
   (`_check_required`, `_check_permission_overrun`, `_check_scope_overlap`,
   `_check_missing_evidence_plan`) so each one is independently testable
   and the verdict logic is obvious.

3. Risk envelope generation (`make_risk_envelope`) is a pure function
   with no I/O — the v2 hook (`goal_guard_hook.write_risk_envelope`)
   owns the file write.  This keeps the guard logic unit-testable
   without filesystem fixtures.

Forbidden paths (check 3) come from F000 spec §7 (red lines) and are
hard-coded here so they cannot drift: any Goal whose scope tries to
touch the verifier or AGENTS.md is FATAL.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class GuardVerdict(str, Enum):
    """Guard verdict (3-way).

    PASS        — GoalContract is complete; dispatch as normal.
    RISK_BLOCK  — GoalContract is incomplete but recoverable; write a
                  risk envelope and skip this dispatch.
    FATAL       — GoalContract tries to overstep boundaries (e.g. allow
                  access to verifier/deterministic.py or AGENTS.md);
                  isolate the envelope and never retry.
    """

    PASS = "pass"
    RISK_BLOCK = "risk_block"
    FATAL = "fatal"


# ---------------------------------------------------------------- Forbid list
# Paths that NO GoalContract is allowed to claim in its permission_scope.
# Sourced from F000 spec §7 "不动红线" + the cross-agent hard rules.
# Both forward-slash and back-slash variants are checked.
_FORBIDDEN_PATH_PREFIXES: ClassVar[tuple[str, ...]] = (
    "D:/AIOS/kernel/src/aios_kernel/verifier/",
    "D:\\AIOS\\kernel\\src\\aios_kernel\\verifier\\",
    "D:/AIOS/_agent-hub/AGENTS.md",
    "D:\\AIOS\\_agent-hub\\AGENTS.md",
)


# ---------------------------------------------------------------- GoalContract
@dataclass
class OpType:
    """An (domain, action) pair used for autonomous_scope and requires_authorization."""

    domain: str
    action: str

    def as_pair(self) -> tuple[str, str]:
        return (self.domain, self.action)


@dataclass
class EvidenceRequest:
    """Missing-evidence entry.  `required` says whether the guard
    should flag this as a blocker (no required=True entry ⇒ "no
    collection plan" failure).
    """

    name: str
    required: bool = True


@dataclass
class FailureMode:
    """A failure-trap declared up front to avoid the "surface success" pitfall."""

    name: str
    severity: str = "medium"  # low | medium | high | critical


@dataclass
class PermissionScope:
    """The set of paths / operations a Goal is allowed to touch."""

    allowed_paths: list[str] = field(default_factory=list)
    allowed_ops: list[str] = field(default_factory=list)


@dataclass
class GoalContract:
    """Minimal GoalContract shape used by GoalGuard.

    F001 will eventually expose this on the real Goal aggregate (12
    fields).  Until then we keep our own dataclass; the guard accepts
    BOTH a GoalContract and a duck-typed object (Goal / dict / namespace)
    via _coerce().
    """

    id: str = ""
    title: str = ""
    success_criteria: str = ""
    budget: float = 0.0
    owner: str = ""
    status: str = "Pending"
    permission_scope: PermissionScope = field(default_factory=PermissionScope)
    failure_modes: list[FailureMode] = field(default_factory=list)
    missing_evidence: list[EvidenceRequest] = field(default_factory=list)
    autonomous_scope: list[OpType] = field(default_factory=list)
    requires_authorization: list[OpType] = field(default_factory=list)


# ---------------------------------------------------------------- GuardReport
@dataclass
class GuardReport:
    """What GoalGuard.validate returns.

    `risk_envelope` is populated only when verdict=RISK_BLOCK; the v2
    hook writes it to v2/messages/risk/.
    """

    verdict: GuardVerdict
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    risk_envelope: dict | None = None

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "passed": list(self.passed_checks),
            "failed": list(self.failed_checks),
            "risk_envelope": self.risk_envelope,
        }


# ---------------------------------------------------------------- Coercion
@dataclass
class _ContractView:
    """Internal flat view of any contract-ish input.  GoalGuard only
    talks to this view, never to the raw input.  This is what makes the
    guard duck-typed and forward-compatible with F001's eventual 12-field
    Goal extension.
    """

    title: Any = None
    success_criteria: Any = None
    budget: Any = None
    owner: Any = None
    status: Any = None
    permission_scope: Any = None
    failure_modes: Any = None
    missing_evidence: Any = None
    autonomous_scope: Any = None
    requires_authorization: Any = None


def _coerce(contract: Any) -> _ContractView:
    """Build a _ContractView from a GoalContract / Goal / dict / None."""
    if contract is None:
        return _ContractView()
    if isinstance(contract, GoalContract):
        return _ContractView(
            title=contract.title,
            success_criteria=contract.success_criteria,
            budget=contract.budget,
            owner=contract.owner,
            status=contract.status,
            permission_scope=contract.permission_scope,
            failure_modes=list(contract.failure_modes or []),
            missing_evidence=list(contract.missing_evidence or []),
            autonomous_scope=list(contract.autonomous_scope or []),
            requires_authorization=list(contract.requires_authorization or []),
        )
    if isinstance(contract, dict):
        ps = contract.get("permission_scope") or {}
        return _ContractView(
            title=contract.get("title"),
            success_criteria=contract.get("success_criteria"),
            budget=contract.get("budget"),
            owner=contract.get("owner"),
            status=contract.get("status"),
            permission_scope=_coerce_permission_scope(ps),
            failure_modes=list(contract.get("failure_modes") or []),
            missing_evidence=list(contract.get("missing_evidence") or []),
            autonomous_scope=list(contract.get("autonomous_scope") or []),
            requires_authorization=list(contract.get("requires_authorization") or []),
        )
    # Generic object (Goal, namespace, mock...) — duck type via getattr.
    ps = getattr(contract, "permission_scope", None)
    if ps is None and hasattr(contract, "metadata"):
        # Some sources stash scope inside metadata.permission_scope
        md = getattr(contract, "metadata", {}) or {}
        ps = md.get("permission_scope") if isinstance(md, dict) else None
    return _ContractView(
        title=getattr(contract, "title", None),
        success_criteria=getattr(contract, "success_criteria", None),
        budget=getattr(contract, "budget", None),
        owner=getattr(contract, "owner", None),
        status=getattr(contract, "status", None),
        permission_scope=_coerce_permission_scope(ps),
        failure_modes=list(getattr(contract, "failure_modes", []) or []),
        missing_evidence=list(getattr(contract, "missing_evidence", []) or []),
        autonomous_scope=list(getattr(contract, "autonomous_scope", []) or []),
        requires_authorization=list(getattr(contract, "requires_authorization", []) or []),
    )


def _coerce_permission_scope(value: Any) -> PermissionScope | None:
    if value is None:
        return None
    if isinstance(value, PermissionScope):
        return value
    if isinstance(value, dict):
        return PermissionScope(
            allowed_paths=list(value.get("allowed_paths") or []),
            allowed_ops=list(value.get("allowed_ops") or []),
        )
    return PermissionScope(
        allowed_paths=list(getattr(value, "allowed_paths", []) or []),
        allowed_ops=list(getattr(value, "allowed_ops", []) or []),
    )


def _pair(op: Any) -> tuple[str, str]:
    """Normalize an OpType-shaped thing to a (domain, action) tuple."""
    if op is None:
        return ("", "")
    if isinstance(op, OpType):
        return op.as_pair()
    if isinstance(op, dict):
        return (str(op.get("domain", "")), str(op.get("action", "")))
    return (str(getattr(op, "domain", "")), str(getattr(op, "action", "")))


# ---------------------------------------------------------------- GoalGuard
class GoalGuard:
    """Validate a GoalContract before v2 consumer dispatch.

    Usage:
        guard = GoalGuard()
        report = guard.validate(contract)
        if report.verdict == GuardVerdict.PASS:
            ...dispatch...
        elif report.verdict == GuardVerdict.RISK_BLOCK:
            write_risk_envelope(report.risk_envelope)
        else:  # FATAL
            deadletter(...)
    """

    # 10 required fields per F000 spec §2 (autonomous_scope and
    # requires_authorization count as 2 of the 10; stated_goal +
    # inferred_intent map to title + success_criteria; approved_tradeoffs
    # is optional and not enforced here).
    REQUIRED_FIELDS: ClassVar[tuple[str, ...]] = (
        "title",
        "success_criteria",
        "budget",
        "owner",
        "status",
        "permission_scope",
        "failure_modes",
        "missing_evidence",
        "autonomous_scope",
        "requires_authorization",
    )

    def __init__(self, knowledge_service: Any = None):
        """Initialize the guard.

        Parameters
        ----------
        knowledge_service : CrossAgentKnowledgeService | None
            Optional Phase G G003 cross-agent knowledge service. When set,
            ``validate()`` will (READ-ONLY, never mutating) reference the
            5-agent failure cluster + capability index to enrich the audit
            trail. When None (default), behavior is identical to F005
            (backward-compatible).
        """
        self.knowledge = knowledge_service

    def validate(self, contract: Any) -> GuardReport:
        """Run all 5 checks and return a GuardReport.

        Accepts:
          - GoalContract instance
          - Goal (or any object with the required attrs via getattr)
          - dict with the same keys
          - None → treated as missing everything → FATAL
        """
        passed: list[str] = []
        failed: list[str] = []
        view = _coerce(contract)

        # Check 1: 必填字段完整性
        missing = self._check_required(view)
        if not missing:
            passed.append("required_fields_complete")
        else:
            failed.append(f"required_fields_missing: {missing}")

        # Check 2: 失败陷阱（surface success trap）非空
        if view.failure_modes:
            passed.append("failure_modes_present")
        else:
            failed.append("failure_modes_empty (surface success trap risk)")

        # Check 3: 权限范围越权检测
        overrun = self._check_permission_overrun(view)
        if not overrun:
            passed.append("permission_scope_in_bounds")
        else:
            failed.append(f"permission_overrun: {overrun}")

        # Check 4: autonomous_scope vs requires_authorization 不重叠
        overlap = self._check_scope_overlap(view)
        if not overlap:
            passed.append("autonomous_vs_authorization_disjoint")
        else:
            failed.append(f"scope_overlap: {overlap}")

        # Check 5: 缺失证据非空 → 必须有采集计划（required=True 项）
        if not view.missing_evidence:
            passed.append("missing_evidence_empty_ok")
        else:
            if self._check_missing_evidence_plan(view):
                passed.append("missing_evidence_has_collection_plan")
            else:
                failed.append("missing_evidence_no_collection_plan")

        # Phase G G003: cross-agent knowledge reference (READ-ONLY, NEVER mutates).
        # For each FailureMode declared by the contract, ask the knowledge service
        # if any of the 5 agents has already seen that failure. Pure audit signal —
        # never affects the 5-check verdict logic above.
        self._reference_cross_agent_knowledge(view, passed)

        # Verdict logic: any overrun failure → FATAL; any other failure → RISK_BLOCK; all pass → PASS
        if not failed:
            return GuardReport(GuardVerdict.PASS, passed, [])
        if any("overrun" in f or "forbidden" in f for f in failed):
            return GuardReport(GuardVerdict.FATAL, passed, failed)
        return GuardReport(GuardVerdict.RISK_BLOCK, passed, failed)

    # ----- G003 cross-agent knowledge reference (read-only) ----------------

    def _reference_cross_agent_knowledge(self, view: _ContractView, passed: list[str]) -> None:
        """Phase G G003: enrich the audit trail with cross-agent failure signal.

        - READ-ONLY: never mutates the knowledge service or the contract
        - NEVER changes the 5-check verdict logic
        - Gracefully degrades when service is missing / IO fails
        """
        if self.knowledge is None:
            return
        # Duck-typed interface — accept any object with has_any_agent_seen_failure()
        has_fn = getattr(self.knowledge, "has_any_agent_seen_failure", None)
        if not callable(has_fn):
            return
        seen_count = 0
        for mode in view.failure_modes or []:
            name: str | None = None
            if isinstance(mode, dict):
                name = mode.get("name")
            else:
                name = getattr(mode, "name", None)
            if not name:
                continue
            try:
                if has_fn(str(name)):
                    seen_count += 1
            except Exception:
                # IO/serialization failure must NEVER break dispatch
                continue
        if seen_count:
            passed.append(
                f"cross_agent_knowledge_referenced: {seen_count}/{len(view.failure_modes)} failure_modes seen by other agents"
            )

    # ----- individual checks ------------------------------------------------

    def _check_required(self, view: _ContractView) -> list[str]:
        missing: list[str] = []
        for fname in self.REQUIRED_FIELDS:
            value = getattr(view, fname, None)
            if value is None:
                missing.append(fname)
                continue
            # Empty list / empty string counts as missing (budget=0.0 is valid)
            if isinstance(value, (list, tuple, str)) and len(value) == 0:
                missing.append(fname)
        return missing

    def _check_permission_overrun(self, view: _ContractView) -> list[str]:
        scope = view.permission_scope
        if scope is None:
            return ["permission_scope_missing"]
        allowed = list(getattr(scope, "allowed_paths", []) or [])
        if not allowed:
            return ["permission_scope_empty"]
        issues: list[str] = []
        for path in allowed:
            norm_path = path.replace("\\", "/")
            for forbidden in _FORBIDDEN_PATH_PREFIXES:
                norm_forbidden = forbidden.replace("\\", "/")
                if norm_path.startswith(norm_forbidden) or norm_path == norm_forbidden.rstrip("/"):
                    issues.append(f"forbidden_path_access: {path}")
                    break
        return issues

    def _check_scope_overlap(self, view: _ContractView) -> list[dict]:
        auto_pairs = {_pair(o) for o in (view.autonomous_scope or [])}
        auth_pairs = {_pair(o) for o in (view.requires_authorization or [])}
        overlap = auto_pairs & auth_pairs
        return [{"domain": d, "action": a} for (d, a) in sorted(overlap)]

    def _check_missing_evidence_plan(self, view: _ContractView) -> bool:
        """Return True iff at least one missing_evidence entry has required=True.

        Entries can be EvidenceRequest dataclass instances OR plain dicts
        (when the contract arrived as JSON).  Both are accepted here.
        """
        for entry in view.missing_evidence or []:
            if entry is None:
                continue
            if isinstance(entry, dict):
                if bool(entry.get("required", False)):
                    return True
            else:
                if bool(getattr(entry, "required", False)):
                    return True
        return False


# ---------------------------------------------------------------- Risk envelope
def make_risk_envelope(contract: Any, report: GuardReport, original_envelope: dict) -> dict:
    """Build the `goal_guard_risk` audit envelope.

    This is a pure function — no I/O.  The v2 hook layer is responsible
    for writing it to disk.
    """
    goal_id = ""
    if isinstance(contract, GoalContract):
        goal_id = contract.id
    elif isinstance(contract, dict):
        goal_id = str(contract.get("id") or "")
    else:
        goal_id = str(getattr(contract, "id", "") or "")
    return {
        "type": "goal_guard_risk",
        "goal_id": goal_id,
        "verdict": report.verdict.value,
        "failed_checks": list(report.failed_checks),
        "passed_checks": list(report.passed_checks),
        "original_envelope_id": original_envelope.get("id") if isinstance(original_envelope, dict) else None,
        "original_envelope_type": original_envelope.get("message_type") if isinstance(original_envelope, dict) else None,
        "created_at": _now_iso(),
        "ts": _now_iso(),
    }


def _now_iso() -> str:
    """Local ISO timestamp (no UTC dep, no extra imports)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


__all__ = [
    "GuardVerdict",
    "GuardReport",
    "GoalGuard",
    "GoalContract",
    "PermissionScope",
    "FailureMode",
    "EvidenceRequest",
    "OpType",
    "make_risk_envelope",
]