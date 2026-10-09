"""parser.py - F002 IntentParser + GoalContract (12-field schema).

This module owns the public IntentParser API:

    IntentParser(llm_adapter=None, rule_db=None).parse(text, ctx) -> GoalContract

The 12-field GoalContract type matches F000 Phase F Acceptance Spec §2
verbatim. F001 (GoalContract 完整化) is running in parallel; once F001
lands and adds the same field set to ``aios_kernel.domain.Goal``, an
adapter (``GoalContract.to_domain_goal()``) can convert intent-side
GoalContract -> domain-side Goal. **F002 does NOT modify domain/goal.py**.

Pydantic types defined here (mirror F001's eventual schema):

    OpType              domain x action x optional target
    Constraint          type x value x rationale
    EnvSnapshot         cwd x os x available_tools x recent_failures x history_refs
    FailureMode         description x detection x optional indicator
    PermissionScope     allowed_paths x allowed_ops x max_budget x max_duration_sec
    EvidenceRequest     description x source x required (default True)
    Tradeoff            decision x cost x benefit x approved_by
    GoalContract        the 12-field result of IntentParser.parse()

Pure rule path (NullLLMAdapter is the default) covers all 5 input
categories in F002 §Evidence Requirements:
    command / statement / question / constrained / tradeoff
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from aios_kernel.intent.classifier import IntentType
from aios_kernel.intent.llm_adapter import LLMAdapter, NullLLMAdapter
from aios_kernel.intent.rules import (
    classify_by_rules,
    extract_constraints,
    extract_tradeoffs,
)


# ---------------------------------------------------------------------------
# Pydantic types — mirror F001's eventual schema (F000 §2)
# ---------------------------------------------------------------------------

ConstraintType = Literal["budget", "timeout", "forbidden_path", "rate_limit", "scope"]
OpDomain = Literal["file", "network", "service", "data", "config"]
OpAction = Literal["read", "write", "execute", "delete", "modify"]


class OpType(BaseModel):
    """(domain, action, target) triple describing one allowed op."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    domain: OpDomain
    action: OpAction
    target: str | None = None


class Constraint(BaseModel):
    """A constraint extracted from the user text (or environment)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    type: ConstraintType
    value: Any
    rationale: str = ""


class EnvSnapshot(BaseModel):
    """Environment context for the GoalContract (F000 §2 row 5).

    Either provided by the caller (``parse(..., context=EnvSnapshot(...))``)
    or built by the parser from ``os.getcwd()`` + ``sys.platform`` when
    the caller omits it. ``recent_failures`` / ``history_refs`` are
    append-only and default to empty lists so a fresh parse always works.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    cwd: str
    os: str
    available_tools: list[str] = Field(default_factory=list)
    recent_failures: list[str] = Field(default_factory=list)
    history_refs: list[str] = Field(default_factory=list)


class FailureMode(BaseModel):
    """A named way the goal could 'succeed' on paper but actually fail."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    description: str
    detection: str
    indicator: str | None = None


class PermissionScope(BaseModel):
    """Static permission cap for the goal (F000 §2 row 8)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    allowed_paths: list[str] = Field(default_factory=list)
    allowed_ops: list[str] = Field(default_factory=list)
    max_budget: float = Field(default=0.0, ge=0.0)
    max_duration_sec: int | None = None
    requires_approval: list[str] = Field(default_factory=list)


class EvidenceRequest(BaseModel):
    """What we still need to know before confidently executing (F000 §2 row 9)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    description: str
    source: str
    required: bool = True


class Tradeoff(BaseModel):
    """A user-approved sacrifice (F000 §2 row 10)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    decision: str
    cost: str
    benefit: str
    approved_by: str = "user"


class GoalContract(BaseModel):
    """The 12-field contract produced by IntentParser.parse().

    Order matches F000 Phase F Acceptance Spec §2 table:

        1.  stated_goal
        2.  inferred_intent
        3.  preserve_capabilities
        4.  known_constraints
        5.  environment_context
        6.  success_criteria
        7.  failure_modes
        8.  permission_scope
        9.  missing_evidence
        10. approved_tradeoffs
        11. autonomous_scope
        12. requires_authorization
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # 1
    stated_goal: str = Field(..., min_length=1, max_length=2000)
    # 2
    inferred_intent: str | None = None
    # 3
    preserve_capabilities: list[str] = Field(default_factory=list)
    # 4
    known_constraints: list[Constraint] = Field(default_factory=list)
    # 5
    environment_context: EnvSnapshot | None = None
    # 6
    success_criteria: str = Field(
        ..., min_length=1, max_length=1000,
        description="How we know the goal succeeded.",
    )
    # 7
    failure_modes: list[FailureMode] = Field(default_factory=list)
    # 8
    permission_scope: PermissionScope | None = None
    # 9
    missing_evidence: list[EvidenceRequest] = Field(default_factory=list)
    # 10
    approved_tradeoffs: list[Tradeoff] = Field(default_factory=list)
    # 11
    autonomous_scope: list[OpType] = Field(default_factory=list)
    # 12
    requires_authorization: list[OpType] = Field(default_factory=list)

    # ----- non-schema helpers (test-friendly) -----------------------------

    @property
    def intent_type(self) -> IntentType:
        """Heuristic — surface the parser's classification for downstream code."""
        meta = self._meta or {}
        t = meta.get("intent_type")
        if isinstance(t, IntentType):
            return t
        return IntentType.UNKNOWN

    # private stash so we can round-trip intent_type without polluting the schema
    _meta: dict[str, Any] | None = None

    def with_meta(self, meta: dict[str, Any]) -> "GoalContract":
        """Return a copy with ``_meta`` attached (for test introspection)."""
        # Pydantic forbids extras; we mutate the private attr instead.
        # Pydantic copy is the supported way; do not bypass with __dict__.
        cp = self.model_copy(deep=True)
        cp._meta = dict(meta)
        return cp


# ---------------------------------------------------------------------------
# IntentParser
# ---------------------------------------------------------------------------


# Default success_criteria templates per intent type. Templates are short;
# downstream code (or a downstream LLM) refines them per task.

_SUCCESS_CRITERIA_TEMPLATES: dict[IntentType, str] = {
    IntentType.COMMAND: "Action completed as stated and verified by deterministic check.",
    IntentType.STATEMENT: "Stated need is addressed; deliverables produced.",
    IntentType.QUESTION: "Question answered with cited sources and reproducible reasoning.",
    IntentType.CONSTRAINED: "Action completed within every stated constraint.",
    IntentType.TRADEOFF: "Action completed; the approved tradeoff is respected.",
    IntentType.UNKNOWN: "Goal achieved without violating defaults; user to confirm scope.",
}


# Default permission_scope per intent type (conservative defaults).

_PERMISSION_SCOPE_DEFAULTS: dict[IntentType, PermissionScope] = {
    IntentType.COMMAND: PermissionScope(
        allowed_paths=[],
        allowed_ops=["read", "write"],
        max_budget=100.0,
        max_duration_sec=3600,
        requires_approval=["execute", "delete"],
    ),
    IntentType.STATEMENT: PermissionScope(
        allowed_paths=[],
        allowed_ops=["read"],
        max_budget=50.0,
        max_duration_sec=1800,
        requires_approval=["write", "execute", "delete"],
    ),
    IntentType.QUESTION: PermissionScope(
        allowed_paths=[],
        allowed_ops=["read"],
        max_budget=0.0,
        max_duration_sec=600,
        requires_approval=["write", "execute", "delete"],
    ),
    IntentType.CONSTRAINED: PermissionScope(
        allowed_paths=[],
        allowed_ops=["read", "write"],
        max_budget=50.0,
        max_duration_sec=1800,
        requires_approval=["execute", "delete"],
    ),
    IntentType.TRADEOFF: PermissionScope(
        allowed_paths=[],
        allowed_ops=["read", "write"],
        max_budget=50.0,
        max_duration_sec=1800,
        requires_approval=["execute", "delete"],
    ),
    IntentType.UNKNOWN: PermissionScope(
        allowed_paths=[],
        allowed_ops=["read"],
        max_budget=0.0,
        max_duration_sec=300,
        requires_approval=["write", "execute", "delete"],
    ),
}


# Default autonomous_scope (what we can do without asking) per intent type.

_AUTONOMOUS_SCOPE_DEFAULTS: dict[IntentType, list[OpType]] = {
    IntentType.COMMAND: [OpType(domain="file", action="read")],
    IntentType.STATEMENT: [OpType(domain="file", action="read")],
    IntentType.QUESTION: [OpType(domain="file", action="read"), OpType(domain="data", action="read")],
    IntentType.CONSTRAINED: [OpType(domain="file", action="read")],
    IntentType.TRADEOFF: [OpType(domain="file", action="read")],
    IntentType.UNKNOWN: [OpType(domain="file", action="read")],
}


# Default requires_authorization per intent type.

_REQUIRES_AUTH_DEFAULTS: dict[IntentType, list[OpType]] = {
    IntentType.COMMAND: [
        OpType(domain="file", action="write"),
        OpType(domain="file", action="execute"),
        OpType(domain="file", action="delete"),
        OpType(domain="network", action="execute"),
    ],
    IntentType.STATEMENT: [
        OpType(domain="file", action="write"),
        OpType(domain="file", action="execute"),
        OpType(domain="file", action="delete"),
    ],
    IntentType.QUESTION: [],
    IntentType.CONSTRAINED: [
        OpType(domain="file", action="execute"),
        OpType(domain="file", action="delete"),
    ],
    IntentType.TRADEOFF: [
        OpType(domain="file", action="execute"),
        OpType(domain="file", action="delete"),
    ],
    IntentType.UNKNOWN: [
        OpType(domain="file", action="write"),
        OpType(domain="file", action="execute"),
        OpType(domain="file", action="delete"),
    ],
}


# Heuristic: map raw constraint.type strings (from rules.py) -> Pydantic Literal
#   "budget"     -> "budget"
#   "timeout"    -> "timeout"
#   "scope"      -> "scope"
#   "priority_high" -> "rate_limit"  (priority is enforced via rate_limit bucket)
_RAW_CONSTRAINT_MAP: dict[str, str] = {
    "budget": "budget",
    "timeout": "timeout",
    "scope": "scope",
    "priority_high": "rate_limit",
}


# Detect forbidden-path scope constraints: "不要 X" where X looks like a path.

_PATH_HINT = re.compile(r"[A-Za-z]:[\\\\/]|/|\.py|\.md|\.json|\.toml|\.yaml|\.yml")


def _scope_value_to_constraint(value: str, rationale: str) -> Constraint | None:
    """Decide if a 'scope' raw match is a forbidden_path or generic scope."""
    v = value.strip()
    if not v:
        return None
    if _PATH_HINT.search(v) or v.startswith(("./", "../", "~/", "$")):
        return Constraint(type="forbidden_path", value=v, rationale=rationale)
    return Constraint(type="scope", value=v, rationale=rationale)


class IntentParser:
    """用户文本 → GoalContract 解析器（rule + LLM hybrid）.

    Args:
        llm_adapter: Optional LLM fallback (Protocol). When ``None`` (the
            default) we use :class:`NullLLMAdapter` so F002 ships with
            **zero external LLM dependency**.
        rule_db: Reserved for future rule packs. Today the regex
            constants from :mod:`aios_kernel.intent.rules` are the only
            rule source, so this argument is ignored but accepted for
            forward compatibility (F005/Future may inject a richer
            rule_db).
        default_owner: Default ``owner`` string used for the synthetic
            GoalContract. F002 doesn't take an Envelope; the owner is
            surfaced via GoalContract metadata.
    """

    def __init__(
        self,
        llm_adapter: LLMAdapter | None = None,
        rule_db: Any = None,
        default_owner: str = "claudecode",
    ) -> None:
        self.llm: LLMAdapter = llm_adapter if llm_adapter is not None else NullLLMAdapter()
        self.rule_db = rule_db  # reserved; ignored today
        self.default_owner = default_owner

    # ------------------------------------------------------------------ API

    def parse(
        self,
        user_text: str,
        context: EnvSnapshot | None = None,
    ) -> GoalContract:
        """Parse ``user_text`` into a 12-field :class:`GoalContract`.

        Flow (per F002 card §Scope 1):
            1. rule-based preprocessing (classify + extract)
            2. extract stated_goal (always = user_text, possibly trimmed)
            3. extract known_constraints (regex)
            4. extract approved_tradeoffs (regex)
            5. extract inferred_intent (LLM fillin; rule gives candidate)
            6. mark missing_evidence (rule failed items)
            7. mark permission_scope (default conservative)
            8. mark autonomous_scope / requires_authorization (intent-typed)
        """
        text = (user_text or "").strip()
        if not text:
            # Empty input: still produce a valid GoalContract but flag
            # missing_evidence heavily.
            return self._build_empty_contract(context)

        # 1. Intent classification (rule first; LLM as tie-breaker)
        intent_type = classify_by_rules(text)
        if intent_type is IntentType.UNKNOWN and self.llm is not None:
            llm_type = self.llm.classify_intent(text)
            if isinstance(llm_type, IntentType):
                intent_type = llm_type

        # 2-3. Extract constraints
        raw_constraints = extract_constraints(text)
        # If tradeoffs are detected, suppress scope-constraints that overlap
        # with the tradeoff raw match (e.g. "宁可慢 不要出错" should NOT
        # also yield a scope-constraint "不要 出错").
        raw_tradeoffs_early = extract_tradeoffs(text)
        tradeoff_blobs = {t["_raw"] for t in raw_tradeoffs_early}
        constraints: list[Constraint] = []
        for raw in raw_constraints:
            rtype = raw["type"]
            value = raw["value"]
            rationale = raw.get("rationale", "")
            mapped = _RAW_CONSTRAINT_MAP.get(rtype)
            if mapped == "forbidden_path" or (mapped == "scope" and (not value or _PATH_HINT.search(value))):
                c = _scope_value_to_constraint(value, rationale) if value else None
                if c is not None:
                    constraints.append(c)
                continue
            # Dedup against tradeoff overlap (avoid "不要 出错" appearing
            # as both a tradeoff AND a scope constraint).
            if value and any(value in blob for blob in tradeoff_blobs):
                continue
            if mapped is None:
                # unknown raw type -> skip (would fail Pydantic Literal)
                continue
            if mapped == "budget":
                try:
                    v = float(value)
                except (TypeError, ValueError):
                    v = 0.0
                constraints.append(Constraint(type="budget", value=v, rationale=rationale))
            elif mapped == "timeout":
                # Convert "<n> 分钟/小时/天/秒" -> seconds
                secs = _parse_duration_seconds(text)
                if secs is not None:
                    constraints.append(Constraint(type="timeout", value=secs, rationale=rationale))
            elif mapped == "scope":
                c = _scope_value_to_constraint(value, rationale)
                if c is not None:
                    constraints.append(c)
            elif mapped == "rate_limit":
                constraints.append(Constraint(type="rate_limit", value="high", rationale=rationale))

        # 4. Extract tradeoffs
        raw_tradeoffs = extract_tradeoffs(text)
        tradeoffs: list[Tradeoff] = []
        for raw in raw_tradeoffs:
            ttype = raw["type"]
            decision = raw["decision"]
            cost = raw["cost"]
            if not decision and not cost:
                continue
            tradeoffs.append(Tradeoff(
                decision=decision or ttype,
                cost=cost or "(implicit)",
                benefit=raw.get("benefit", "implicit (user stated)"),
                approved_by=raw.get("approved_by", "user"),
            ))

        # 5. Inferred intent (LLM fillin; rule gives candidate)
        rule_candidate = _rule_based_inferred_intent(text, intent_type)
        inferred = None
        if self.llm is not None and rule_candidate:
            candidates = [rule_candidate, _alt_candidate(intent_type)]
            try:
                inferred = self.llm.infer_intent(text, candidates)
            except Exception:
                inferred = None
        if inferred is None:
            inferred = rule_candidate

        # 6. Missing evidence (only if we couldn't extract something)
        missing: list[EvidenceRequest] = []
        if intent_type is IntentType.UNKNOWN:
            missing.append(EvidenceRequest(
                description="Could not classify intent from user text",
                source="user_input",
                required=True,
            ))
        if intent_type is IntentType.STATEMENT and not constraints and not tradeoffs:
            missing.append(EvidenceRequest(
                description="Statement lacks measurable success criteria; ask user for explicit goal",
                source="user_input",
                required=False,
            ))
        if intent_type is IntentType.QUESTION and not inferred:
            missing.append(EvidenceRequest(
                description="Question needs an LLM-or-knowledge-base lookup to answer",
                source="knowledge_base",
                required=True,
            ))

        # 7-8. Permission scope + autonomous_scope / requires_authorization
        perm = _PERMISSION_SCOPE_DEFAULTS[intent_type]
        # If a budget constraint is present, raise max_budget to at least that value
        budget_cap = next(
            (c.value for c in constraints if c.type == "budget"),
            None,
        )
        if isinstance(budget_cap, (int, float)) and budget_cap > perm.max_budget:
            perm = perm.model_copy(update={"max_budget": float(budget_cap)})
        # If a timeout constraint is present, raise max_duration_sec
        dur = next((c.value for c in constraints if c.type == "timeout"), None)
        if isinstance(dur, int) and dur > 0:
            perm = perm.model_copy(update={"max_duration_sec": dur})

        # EnvSnapshot (caller-supplied or default)
        if context is None:
            context = _default_env_snapshot()

        # Build the contract
        contract = GoalContract(
            stated_goal=text,
            inferred_intent=inferred,
            preserve_capabilities=[],
            known_constraints=constraints,
            environment_context=context,
            success_criteria=_SUCCESS_CRITERIA_TEMPLATES[intent_type],
            failure_modes=_default_failure_modes(intent_type),
            permission_scope=perm,
            missing_evidence=missing,
            approved_tradeoffs=tradeoffs,
            autonomous_scope=list(_AUTONOMOUS_SCOPE_DEFAULTS[intent_type]),
            requires_authorization=list(_REQUIRES_AUTH_DEFAULTS[intent_type]),
        )
        # attach _meta so downstream code/tests can introspect intent_type
        return contract.with_meta({
            "intent_type": intent_type,
            "owner": self.default_owner,
            "parsed_at": datetime.now(UTC).isoformat(),
        })

    # -------------------------------------------------------------- helpers

    def _build_empty_contract(self, context: EnvSnapshot | None) -> GoalContract:
        ctx = context or _default_env_snapshot()
        contract = GoalContract(
            stated_goal="(empty user input)",
            inferred_intent=None,
            environment_context=ctx,
            success_criteria=_SUCCESS_CRITERIA_TEMPLATES[IntentType.UNKNOWN],
            permission_scope=_PERMISSION_SCOPE_DEFAULTS[IntentType.UNKNOWN],
            missing_evidence=[EvidenceRequest(
                description="User provided empty input; please supply the actual goal",
                source="user_input",
                required=True,
            )],
            autonomous_scope=list(_AUTONOMOUS_SCOPE_DEFAULTS[IntentType.UNKNOWN]),
            requires_authorization=list(_REQUIRES_AUTH_DEFAULTS[IntentType.UNKNOWN]),
        )
        return contract.with_meta({
            "intent_type": IntentType.UNKNOWN,
            "owner": self.default_owner,
            "parsed_at": datetime.now(UTC).isoformat(),
        })


# ---------------------------------------------------------------------------
# Module-level helpers (private)
# ---------------------------------------------------------------------------


def _rule_based_inferred_intent(text: str, intent_type: IntentType) -> str | None:
    """Synthesize a short inferred_intent string from rule output."""
    if intent_type is IntentType.UNKNOWN:
        return None
    template = {
        IntentType.COMMAND: "execute the user's imperative request",
        IntentType.STATEMENT: "address the user's stated need",
        IntentType.QUESTION: "answer the user's question",
        IntentType.CONSTRAINED: "execute the action under the stated constraints",
        IntentType.TRADEOFF: "execute the action while honouring the stated tradeoff",
    }
    return template[intent_type]


def _alt_candidate(intent_type: IntentType) -> str:
    return f"fallback: handle as {intent_type.value} per conservative defaults"


def _parse_duration_seconds(text: str) -> int | None:
    """Find the FIRST "<n> <unit>" duration in text and convert to seconds."""
    pat = re.compile(
        r"(\d+(?:\.\d+)?)\s*(分钟|min|分钟钟|小时|h|天|d|秒|s)",
        re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2).lower()
    if unit in ("分钟", "min", "分钟钟"):
        return int(n * 60)
    if unit in ("小时", "h"):
        return int(n * 3600)
    if unit in ("天", "d"):
        return int(n * 86400)
    if unit in ("秒", "s"):
        return int(n)
    return None


def _default_env_snapshot() -> EnvSnapshot:
    """Build a default EnvSnapshot from os.getcwd()/sys.platform."""
    import os
    import sys
    return EnvSnapshot(
        cwd=os.getcwd(),
        os=f"{sys.platform} (python {sys.version_info.major}.{sys.version_info.minor})",
        available_tools=[],
    )


def _default_failure_modes(intent_type: IntentType) -> list[FailureMode]:
    """Return the default 'surface-success trap' list per intent type."""
    common = [
        FailureMode(
            description="Output looks correct but does not match user intent (LLM hallucination)",
            detection="deterministic verifier returns False OR user rejects result",
            indicator="verifier.exit_code != 0",
        ),
    ]
    if intent_type is IntentType.COMMAND:
        return common + [
            FailureMode(
                description="Action runs against wrong target (typo in path/id)",
                detection="diff before/after action does not include expected change",
                indicator="expected_path not in artifact_set",
            ),
        ]
    if intent_type is IntentType.QUESTION:
        return common + [
            FailureMode(
                description="Answer cites sources that do not actually exist",
                detection="validate every URL/source id before returning",
                indicator="url_alive_check == False",
            ),
        ]
    return common


__all__ = [
    # types
    "OpType",
    "Constraint",
    "EnvSnapshot",
    "FailureMode",
    "PermissionScope",
    "EvidenceRequest",
    "Tradeoff",
    "GoalContract",
    # parser
    "IntentParser",
    # constants
    "ConstraintType",
    "OpDomain",
    "OpAction",
]