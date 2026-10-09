"""F002 manual verification dump — 5 input categories + 1 mixed."""
import sys
sys.path.insert(0, "D:/AIOS/kernel/src")

from aios_kernel.intent import IntentParser, IntentType

p = IntentParser()

cases = [
    ("COMMAND", "建一个营销活动"),
    ("STATEMENT", "我需要把今天的工作收尾"),
    ("QUESTION", "怎么让 AIOS 知道用户的目标"),
    ("CONSTRAINED", "在 D:/AIOS 内 不要改 verifier"),
    ("TRADEOFF", "宁可慢 不要出错"),
    ("MIXED", "30 分钟内完成 GoalContract，宁可慢不要出错"),
]

for label, text in cases:
    c = p.parse(text)
    print("=" * 72)
    print(f"INPUT ({label}): {text!r}")
    print("=" * 72)
    print(f"intent_type           : {c.intent_type.value}")
    print(f"stated_goal           : {c.stated_goal!r}")
    print(f"inferred_intent       : {c.inferred_intent!r}")
    print(f"preserve_capabilities : {c.preserve_capabilities}")
    print(f"known_constraints     : {[(ct.type, ct.value) for ct in c.known_constraints]}")
    print(f"environment_context   : cwd={c.environment_context.cwd!r} os={c.environment_context.os!r}")
    print(f"success_criteria      : {c.success_criteria!r}")
    print(f"failure_modes         : {[(fm.description[:40], fm.detection[:40]) for fm in c.failure_modes]}")
    print(f"permission_scope      : ops={c.permission_scope.allowed_ops} budget={c.permission_scope.max_budget} dur={c.permission_scope.max_duration_sec} requires_approval={c.permission_scope.requires_approval}")
    print(f"missing_evidence      : {[(e.description[:60], e.source) for e in c.missing_evidence]}")
    print(f"approved_tradeoffs    : {[(t.decision, t.cost) for t in c.approved_tradeoffs]}")
    print(f"autonomous_scope      : {[(o.domain, o.action) for o in c.autonomous_scope]}")
    print(f"requires_authorization: {[(o.domain, o.action) for o in c.requires_authorization]}")
    print(f"#constraints={len(c.known_constraints)} #tradeoffs={len(c.approved_tradeoffs)} #missing={len(c.missing_evidence)}")
    print()