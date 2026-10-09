"""aios_kernel.intent - F002 Intent Parser (rule + LLM hybrid).

Public surface:

    IntentParser                 the main class
    IntentType                   the 6-class enum (command/statement/...)
    GoalContract                 the 12-field result type
    Constraint, Tradeoff, ...    supporting Pydantic types
    LLMAdapter, NullLLMAdapter   optional LLM injection points

Default usage (no LLM dependency):

    from aios_kernel.intent import IntentParser, GoalContract
    parser = IntentParser()
    contract = parser.parse("30 分钟内完成 P5 V8，宁可慢不要出错")
    # contract.known_constraints -> [Constraint(type="timeout", value=1800, ...)]
    # contract.approved_tradeoffs -> [Tradeoff(decision="慢", cost="出错", ...)]
    # contract.intent_type        -> IntentType.TRADEOFF
"""
from aios_kernel.intent.classifier import IntentType
from aios_kernel.intent.llm_adapter import LLMAdapter, NullLLMAdapter
from aios_kernel.intent.parser import (
    Constraint,
    EnvSnapshot,
    EvidenceRequest,
    FailureMode,
    GoalContract,
    IntentParser,
    OpType,
    PermissionScope,
    Tradeoff,
)
from aios_kernel.intent.rules import (
    CONSTRAINT_PATTERNS,
    INTENT_CLASSIFIER,
    TRADEOFF_PATTERNS,
    classify_by_rules,
    extract_constraints,
    extract_tradeoffs,
)

__all__ = [
    # main API
    "IntentParser",
    "IntentType",
    "GoalContract",
    # types
    "Constraint",
    "EnvSnapshot",
    "EvidenceRequest",
    "FailureMode",
    "OpType",
    "PermissionScope",
    "Tradeoff",
    # adapters
    "LLMAdapter",
    "NullLLMAdapter",
    # rules (re-exported for tests + direct callers)
    "CONSTRAINT_PATTERNS",
    "TRADEOFF_PATTERNS",
    "INTENT_CLASSIFIER",
    "classify_by_rules",
    "extract_constraints",
    "extract_tradeoffs",
]