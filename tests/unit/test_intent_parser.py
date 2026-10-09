"""test_intent_parser.py - F002 Intent Parser unit tests (18+ cases).

Coverage matrix (per F002 card §2 + §Evidence Requirements):

    5 input categories x 3+ cases each = 15+ cases
    + 3 edge cases (mixed, missing evidence, unknown fallback) = 18+

Each test asserts:
  - IntentType matches expected
  - relevant extracted fields are non-empty when applicable
  - GoalContract has all 12 fields populated (even if defaults)

F002 hard rule: tests must run with zero external LLM dependency
(NullLLMAdapter is the default).
"""
from __future__ import annotations

import pytest

from aios_kernel.intent import (
    CONSTRAINT_PATTERNS,
    INTENT_CLASSIFIER,
    IntentParser,
    IntentType,
    LLMAdapter,
    NullLLMAdapter,
    TRADEOFF_PATTERNS,
)
from aios_kernel.intent.parser import (
    Constraint,
    EnvSnapshot,
    FailureMode,
    GoalContract,
    OpType,
    PermissionScope,
    Tradeoff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(text: str) -> GoalContract:
    return IntentParser().parse(text)


def _intent(text: str) -> IntentType:
    return _parse(text).intent_type


# ===========================================================================
# Section 1 — 命令类 (COMMAND) — 3+ cases
# ===========================================================================

class TestCommandCategory:
    """命令类 — imperative verbs (做/写/建/.../立即停止)."""

    def test_parse_command_simple(self):
        c = _parse("建一个营销活动")
        assert c.intent_type is IntentType.COMMAND
        assert c.stated_goal == "建一个营销活动"
        assert c.inferred_intent is not None

    def test_parse_command_with_target(self):
        c = _parse("在 D:/AIOS/kernel 建一个新文件")
        assert c.intent_type is IntentType.CONSTRAINED
        # CONSTRAINED input still has the action embedded in stated_goal
        assert "建" in c.stated_goal
        assert "D:/AIOS/kernel" in c.stated_goal

    def test_parse_command_imperative(self):
        c = _parse("立即停止 v2 consumer")
        assert c.intent_type is IntentType.COMMAND
        assert "v2 consumer" in c.stated_goal

    def test_command_permission_scope_has_write(self):
        c = _parse("写一份周报")
        assert c.intent_type is IntentType.COMMAND
        assert c.permission_scope is not None
        assert "write" in c.permission_scope.allowed_ops
        # COMMAND requires approval for destructive ops
        assert "delete" in c.permission_scope.requires_approval


# ===========================================================================
# Section 2 — 陈述类 (STATEMENT) — 3+ cases
# ===========================================================================

class TestStatementCategory:
    """陈述类 — first-person statements (我需要/我们正在/我想)."""

    def test_parse_statement_need(self):
        c = _parse("我需要把今天的工作收尾")
        assert c.intent_type is IntentType.STATEMENT
        # STATEMENT w/o measurable success -> missing_evidence populated
        assert any(
            "measurable success" in e.description.lower() or "explicit goal" in e.description.lower()
            for e in c.missing_evidence
        )

    def test_parse_statement_progress(self):
        c = _parse("我们正在做 Phase F")
        assert c.intent_type is IntentType.STATEMENT
        assert "Phase F" in c.stated_goal

    def test_parse_statement_intent(self):
        c = _parse("我想了解你的决策过程")
        assert c.intent_type is IntentType.STATEMENT
        assert c.inferred_intent is not None


# ===========================================================================
# Section 3 — 问题类 (QUESTION) — 3+ cases
# ===========================================================================

class TestQuestionCategory:
    """问题类 — interrogative words (怎么/为什么/什么)."""

    def test_parse_question_how(self):
        c = _parse("怎么让 AIOS 知道用户的目标")
        assert c.intent_type is IntentType.QUESTION
        # QUESTION permission_scope is read-only (no destructive ops)
        assert c.permission_scope is not None
        assert c.requires_authorization == []

    def test_parse_question_why(self):
        c = _parse("为什么 GoalContract 需要 12 字段")
        assert c.intent_type is IntentType.QUESTION
        assert "12 字段" in c.stated_goal

    def test_parse_question_what(self):
        c = _parse("什么是 failure_modes")
        assert c.intent_type is IntentType.QUESTION
        assert c.inferred_intent is not None


# ===========================================================================
# Section 4 — 带约束类 (CONSTRAINED) — 3+ cases
# ===========================================================================

class TestConstrainedCategory:
    """带约束类 — budget/timeout/forbidden-path constraints."""

    def test_parse_constrained_path(self):
        c = _parse("在 D:/AIOS 内 不要改 verifier")
        assert c.intent_type is IntentType.CONSTRAINED
        # 改 verifier captured as a scope constraint
        assert any(ct.type in ("scope", "forbidden_path") for ct in c.known_constraints)

    def test_parse_constrained_budget(self):
        c = _parse("预算 ≤500 元 做一个营销工具")
        assert c.intent_type is IntentType.CONSTRAINED
        budgets = [ct for ct in c.known_constraints if ct.type == "budget"]
        assert len(budgets) == 1
        assert budgets[0].value == 500.0
        # budget raised max_budget
        assert c.permission_scope.max_budget >= 500.0

    def test_parse_constrained_timeout(self):
        c = _parse("30 分钟内 完成 P5 V8")
        assert c.intent_type is IntentType.CONSTRAINED
        timeouts = [ct for ct in c.known_constraints if ct.type == "timeout"]
        assert len(timeouts) == 1
        assert timeouts[0].value == 1800  # 30 min * 60 sec
        # timeout raised max_duration_sec
        assert c.permission_scope.max_duration_sec == 1800


# ===========================================================================
# Section 5 — 带取舍类 (TRADEOFF) — 3+ cases
# ===========================================================================

class TestTradeoffCategory:
    """带取舍类 — explicit accepted tradeoffs (宁可 X 不要 Y / 可以 X 换 Y)."""

    def test_parse_tradeoff_ke_neng(self):
        c = _parse("宁可慢 不要出错")
        assert c.intent_type is IntentType.TRADEOFF
        assert len(c.approved_tradeoffs) == 1
        t = c.approved_tradeoffs[0]
        # decision is "慢", cost is "不要出错"
        assert "慢" in t.decision
        assert "出错" in t.cost

    def test_parse_tradeoff_accept(self):
        c = _parse("可以牺牲可读性换性能")
        assert c.intent_type is IntentType.TRADEOFF
        assert len(c.approved_tradeoffs) >= 1

    def test_parse_tradeoff_reject(self):
        c = _parse("不要为了快 牺牲正确性")
        assert c.intent_type is IntentType.TRADEOFF
        # tradeoffs captured (or constraints, depending on regex hit)
        assert (len(c.approved_tradeoffs) >= 1 or len(c.known_constraints) >= 1)


# ===========================================================================
# Section 6 — 混合类 (MIXED) — combines constraints + tradeoffs
# ===========================================================================

class TestMixedInputs:
    """混合输入 — 同时提取 stated_goal + known_constraints + approved_tradeoffs."""

    def test_parse_mixed_command_constraint_tradeoff(self):
        text = "30 分钟内完成 GoalContract，宁可慢不要出错"
        c = _parse(text)
        # The tradeoff regex matches first, so intent = TRADEOFF
        assert c.intent_type is IntentType.TRADEOFF
        # Both timeout constraint AND tradeoff extracted
        assert len(c.known_constraints) >= 1
        assert len(c.approved_tradeoffs) >= 1
        # Cross-check: timeout constraint captured
        assert any(ct.type == "timeout" for ct in c.known_constraints)
        # Cross-check: tradeoff captured
        assert any("慢" in t.decision for t in c.approved_tradeoffs)

    def test_mixed_permission_scope_merged(self):
        """A tradeoff + timeout input must surface timeout in permission_scope."""
        c = _parse("30 分钟内完成 GoalContract，宁可慢不要出错")
        assert c.permission_scope.max_duration_sec == 1800


# ===========================================================================
# Section 7 — 异常 / 边界 (EDGE CASES)
# ===========================================================================

class TestEdgeCases:
    """缺失证据 / 完全无法分类 / 空输入."""

    def test_parse_missing_evidence_detected(self):
        # Statement without measurable success criteria
        c = _parse("我今天要做点东西")
        assert c.intent_type is IntentType.STATEMENT
        assert len(c.missing_evidence) >= 1
        # Each missing_evidence item has source/description fields populated
        for e in c.missing_evidence:
            assert e.description
            assert e.source

    def test_parse_unknown_intent_fallback(self):
        # Pure nonsense — no Chinese keyword matches
        c = _parse("asdofijasodjf")
        assert c.intent_type is IntentType.UNKNOWN
        # missing_evidence flagged
        assert len(c.missing_evidence) >= 1
        # stated_goal still populated (we don't drop the input)
        assert c.stated_goal == "asdofijasodjf"

    def test_parse_empty_input(self):
        c = _parse("")
        assert c.intent_type is IntentType.UNKNOWN
        assert len(c.missing_evidence) >= 1
        # success_criteria + permission_scope populated even for empty input
        assert c.success_criteria  # non-empty
        assert c.permission_scope is not None

    def test_parse_whitespace_only(self):
        c = _parse("   \n\t  ")
        assert c.intent_type is IntentType.UNKNOWN


# ===========================================================================
# Section 8 — Schema completeness (12-field GoalContract)
# ===========================================================================

class TestSchemaCompleteness:
    """GoalContract always has all 12 fields populated (per F000 §2)."""

    def test_all_12_fields_present(self):
        c = _parse("建一个营销活动")
        # 1. stated_goal
        assert c.stated_goal
        # 2. inferred_intent
        # (None is allowed for unknown)
        # 3. preserve_capabilities (default empty list OK)
        assert isinstance(c.preserve_capabilities, list)
        # 4. known_constraints
        assert isinstance(c.known_constraints, list)
        # 5. environment_context
        assert c.environment_context is not None
        # 6. success_criteria
        assert c.success_criteria
        # 7. failure_modes
        assert isinstance(c.failure_modes, list)
        # 8. permission_scope
        assert c.permission_scope is not None
        # 9. missing_evidence
        assert isinstance(c.missing_evidence, list)
        # 10. approved_tradeoffs
        assert isinstance(c.approved_tradeoffs, list)
        # 11. autonomous_scope
        assert isinstance(c.autonomous_scope, list)
        # 12. requires_authorization
        assert isinstance(c.requires_authorization, list)

    def test_env_snapshot_default(self):
        c = _parse("建一个营销活动")
        assert c.environment_context is not None
        assert c.environment_context.cwd  # non-empty
        assert c.environment_context.os   # non-empty

    def test_env_snapshot_caller_supplied(self):
        ctx = EnvSnapshot(cwd="/tmp", os="linux", available_tools=["pytest"])
        c = IntentParser().parse("建一个营销活动", context=ctx)
        assert c.environment_context.cwd == "/tmp"
        assert c.environment_context.available_tools == ["pytest"]


# ===========================================================================
# Section 9 — LLM adapter interface (NullLLMAdapter default)
# ===========================================================================

class TestLLMAdapter:
    """LLMAdapter Protocol + NullLLMAdapter default (no real LLM)."""

    def test_default_adapter_is_null(self):
        p = IntentParser()
        assert isinstance(p.llm, NullLLMAdapter)

    def test_null_adapter_returns_none(self):
        n = NullLLMAdapter()
        assert n.infer_intent("foo", ["bar", "baz"]) is None
        assert n.classify_intent("foo") is None

    def test_null_adapter_records_calls(self):
        # The adapter has a `calls` attribute for test introspection
        n = NullLLMAdapter()
        n.infer_intent("foo", ["bar"])
        n.classify_intent("foo")
        assert len(n.calls) == 2
        assert n.calls[0][0] == "infer_intent"
        assert n.calls[1][0] == "classify_intent"

    def test_custom_adapter_injectable(self):
        class MockAdapter:
            def __init__(self):
                self.calls = []
            def infer_intent(self, text, candidates):
                self.calls.append(("infer", text))
                return candidates[0] if candidates else None
            def classify_intent(self, text):
                self.calls.append(("classify", text))
                return IntentType.COMMAND

        mock = MockAdapter()
        p = IntentParser(llm_adapter=mock)
        c = p.parse("asdofijasodjf")  # UNKNOWN by rule
        # Mock's classify_intent is queried as fallback
        assert mock.calls  # at least one call recorded
        # Mock returns COMMAND, so intent_type should be COMMAND
        assert c.intent_type is IntentType.COMMAND


# ===========================================================================
# Section 10 — Pattern visibility (per Codex Acceptance Gate §4)
# ===========================================================================

class TestPatternsVisible:
    """The 3 pattern tables are importable and non-empty."""

    def test_constraint_patterns_nonempty(self):
        assert len(CONSTRAINT_PATTERNS) >= 3
        # each entry is (compiled regex, type_string)
        for pat, t in CONSTRAINT_PATTERNS:
            assert hasattr(pat, "search")
            assert isinstance(t, str)

    def test_tradeoff_patterns_nonempty(self):
        assert len(TRADEOFF_PATTERNS) >= 1
        for pat, t in TRADEOFF_PATTERNS:
            assert hasattr(pat, "search")
            assert isinstance(t, str)

    def test_intent_classifier_nonempty(self):
        assert len(INTENT_CLASSIFIER) == 5  # 5 typed buckets; UNKNOWN is implicit fallback
        # Each intent type has at least 1 pattern
        for intent_type, patterns in INTENT_CLASSIFIER.items():
            assert len(patterns) >= 1
            for pat in patterns:
                assert hasattr(pat, "search")

    def test_sample_pattern_hits_real_input(self):
        """Per Codex Acceptance Gate §4: '抽样 5 个规则模式 命中真实输入'."""
        # CONSTRAINT_PATTERNS[0] — scope pattern — must match "禁止/不要/避免"
        pat = CONSTRAINT_PATTERNS[0][0]
        assert pat.search("不要 改 verifier")
        assert pat.search("禁止 删除文件")
        assert pat.search("避免 越权")

        # CONSTRAINT_PATTERNS[1] — budget
        pat = CONSTRAINT_PATTERNS[1][0]
        assert pat.search("预算500")
        assert pat.search("预算 ≤100")

        # CONSTRAINT_PATTERNS[2] — timeout
        pat = CONSTRAINT_PATTERNS[2][0]
        assert pat.search("30 分钟")
        assert pat.search("2 小时")

        # TRADEOFF_PATTERNS[0] — approved_tradeoff
        pat = TRADEOFF_PATTERNS[0][0]
        assert pat.search("宁可慢 不要出错")

        # INTENT_CLASSIFIER[COMMAND] — must match "建一个营销活动"
        pat = INTENT_CLASSIFIER[IntentType.COMMAND][0]
        assert pat.search("建一个营销活动")

        # INTENT_CLASSIFIER[QUESTION] — must match "怎么 X"
        pat = INTENT_CLASSIFIER[IntentType.QUESTION][0]
        assert pat.search("怎么 启动")


# ===========================================================================
# Section 11 — FailureMode & OpType type sanity
# ===========================================================================

class TestTypeSanity:
    """Pydantic types validate correctly."""

    def test_op_type_validation(self):
        OpType(domain="file", action="read")
        OpType(domain="network", action="execute", target="https://example.com")
        with pytest.raises(Exception):
            OpType(domain="invalid", action="read")  # type: ignore[arg-type]

    def test_constraint_validation(self):
        Constraint(type="budget", value=100.0, rationale="test")
        Constraint(type="timeout", value=1800, rationale="test")
        Constraint(type="scope", value="no writes", rationale="test")
        with pytest.raises(Exception):
            Constraint(type="invalid", value=1, rationale="x")  # type: ignore[arg-type]

    def test_permission_scope_defaults(self):
        p = PermissionScope(
            allowed_paths=[],
            allowed_ops=["read"],
            max_budget=0.0,
            max_duration_sec=None,
            requires_approval=[],
        )
        assert p.max_budget == 0.0
        assert p.max_duration_sec is None

    def test_tradeoff_basic(self):
        t = Tradeoff(
            decision="慢",
            cost="不要出错",
            benefit="implicit reliability",
            approved_by="user",
        )
        assert t.decision == "慢"
        assert t.cost == "不要出错"
        assert t.approved_by == "user"

    def test_failure_mode_basic(self):
        fm = FailureMode(
            description="looks correct but wrong target",
            detection="verifier returns False",
            indicator="verifier.exit_code != 0",
        )
        assert fm.description
        assert fm.detection