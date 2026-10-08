"""fill_goal_contract.py — Codex Supervisor Goal 实例填充真实字段。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"D:\AIOS\kernel\src")))

from aios_kernel.domain.goal import (
    Goal, GoalStatus, Constraint, EnvSnapshot, FailureMode,
    PermissionScope, EvidenceRequest, Tradeoff, OpType,
)

goal = Goal(
    title="Codex Supervisor 自主运行 (Cognitive Governance)",
    description="Codex 在用户不在场时自主推进：自审计、失败归并、健康监控、写 memory。autonomous_scope 已生效，requires_authorization 列出的需用户拍板。",
    success_criteria="self-audit 每次启动 Codex 自动跑，结果写 memory log，DEGRADED 时按 autonomous_scope 自动修，CLEAN 时无用户介入。",
    budget=0.0,
    owner="codex",

    inferred_intent="用户要的不再是逐条 task card 验收，而是系统自主运行能力 — Phase F 是数据结构层，本 Goal 是运行机制层。",
    preserve_capabilities=[
        "verifier/deterministic.py (don't touch)",
        "v2 consumer main loop (don't refactor)",
        "AGENTS.md SSOT (central truth)",
        "Phase A-F 49+6 Verified cards (don't downgrade)",
        "codex_self_audit.py (autonomous health check)",
    ],
    known_constraints=[
        Constraint(type="timeout", value="self-audit < 5min", rationale="user 期望快速反馈"),
        Constraint(type="forbidden_path", value="D:/AIOS/_agent-hub/AGENTS.md",
                   rationale="SSOT, requires user approval to modify"),
        Constraint(type="scope", value="kernel unit + v2 baseline only",
                   rationale="不跑全 integration suite 太慢"),
    ],
    environment_context=EnvSnapshot(
        cwd="D:/AIOS",
        os="Windows",
        available_tools=["pytest", "preflight", "git", "wmic", "tasklist", "aiosv2 CLI"],
        recent_failures=[
            "v2/src/queue.py shadow stdlib queue (transient)",
            "test_services_persistence.py 3 pre-existing FAIL",
        ],
        history_refs=[
            "Phase F Done report 2026-10-08 23:42",
            "AGENTS.md Phase F section",
        ],
    ),
    failure_modes=[
        FailureMode(description="self-audit 持续 DEGRADED 但无人看见",
                    detection="memory log 连续 3 天无 Codex Self-Audit 段落"),
        FailureMode(description="git dirty 累积超阈值无清理",
                    detection="git status --short 数量 > 200"),
        FailureMode(description="v2 consumer 长跑 daemon 挂掉",
                    detection="wmic 无 v2_consumer / start_consumer_real 进程"),
        FailureMode(description="pytest baseline 退化但无警觉",
                    detection="baseline 测试失败数 > 5 (相对前一天)"),
    ],
    permission_scope=PermissionScope(
        allowed_paths=[
            "D:/AIOS/_agent-hub/scripts/",
            "D:/AIOS/_agent-hub/memory/",
            "D:/AIOS/_agent-hub/reports/",
            "D:/AIOS/aios_tasks/aios_vnext/cards/",
            "D:/AIOS/aios_tasks/aios_vnext/evidence/",
            "D:/AIOS/kernel/tests/unit/",
            "D:/AIOS/kernel/.venv/",
        ],
        allowed_ops=["read", "write", "execute"],
        max_budget=0.0,
        max_duration_sec=300,
        requires_approval=["delete"],
    ),
    missing_evidence=[
        EvidenceRequest(description="v2 consumer 是否真的在长跑",
                        source="tasklist / wmic process query",
                        required=True),
        EvidenceRequest(description="pytest baseline 失败是 pre-existing 还是 regression",
                        source="git log + pytest history",
                        required=True),
        EvidenceRequest(description="用户母令第 4 部分是否补全",
                        source="memory log + new user message",
                        required=False),
    ],
    approved_tradeoffs=[
        Tradeoff(decision="每次 Codex session 启动自动跑 self-audit",
                 cost="启动 latency +5s",
                 benefit="用户不在场时也能发现问题",
                 approved_by="user"),
        Tradeoff(decision="self-audit 不修 pre-existing baseline 失败",
                 cost="DEGRADED 报告里包含已知失败",
                 benefit="不擅自越界改 Phase A-E 已 Verified 范围",
                 approved_by="user (隐含: 不可改 SSOT 已建立)"),
    ],
    # autonomous_scope: 即使 allowed 不够，这些 op 可自主做
    autonomous_scope=[
        OpType(domain="file", action="read"),
        OpType(domain="file", action="write", target="D:/AIOS/_agent-hub/scripts/"),
        OpType(domain="file", action="write", target="D:/AIOS/_agent-hub/memory/"),
        OpType(domain="service", action="execute", target="kernel unit pytest baseline"),
        OpType(domain="data", action="read", target="v2 messages inbox/outbox"),
        OpType(domain="config", action="read", target="aios_kernel.*"),
    ],
    # requires_authorization: 即使在 allowed 内仍需用户拍板
    requires_authorization=[
        OpType(domain="file", action="delete"),
        OpType(domain="file", action="modify", target="D:/AIOS/_agent-hub/AGENTS.md"),
        OpType(domain="file", action="modify", target="kernel/alembic/versions/"),
        OpType(domain="config", action="modify", target="aios_kernel.governance"),
    ],
)

goal.transition_to(GoalStatus.ACTIVE)
print(f"Goal activated: {goal.id[:8]}...")
print(f"autonomous_scope items: {len(goal.autonomous_scope)}")
print(f"requires_authorization items: {len(goal.requires_authorization)}")
print(f"failure_modes items: {len(goal.failure_modes)}")
print()
for f in ['title', 'description', 'inferred_intent', 'preserve_capabilities',
          'known_constraints', 'environment_context', 'success_criteria',
          'failure_modes', 'permission_scope', 'missing_evidence',
          'approved_tradeoffs', 'autonomous_scope', 'requires_authorization']:
    v = getattr(goal, f)
    if isinstance(v, list):
        print(f"  {f}: list[{len(v)}]")
    elif v is None:
        print(f"  {f}: None")
    else:
        print(f"  {f}: {type(v).__name__}")
print()
print(f"Status: {goal.status.value}")
print()

import json
goal_dict = goal.model_dump(mode="json")
goal_dict["status"] = goal.status.value
out_file = Path(r"D:\AIOS\_agent-hub\memory\codex_supervisor_goal.json")
out_file.write_text(json.dumps(goal_dict, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"GoalContract 实例序列化到 {out_file}")
print()
print("Codex Supervisor GoalContract 实例已填充真实字段。")
print("autonomous_scope 已生效 — Codex 可在用户不在场时自主执行。")
print("下次 Codex session 启动时：")
print("  1. 加载这个 JSON")
print("  2. 跑 self-audit (codex_self_audit.py)")
print("  3. 检查 autonomous_scope 内的 baseline")
print("  4. 写 memory log")
print("  5. 不再等用户")