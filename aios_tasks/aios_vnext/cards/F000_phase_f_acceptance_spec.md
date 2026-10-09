---
id: F000
title: Phase F Acceptance Spec v0.1 — Cognitive Governance Plane
owner: Codex
priority: P0
track: 6 — VNext Phase F (Cognitive Governance)
preconditions: [E001, T0032, T0035]
estimated_minutes: 60
depends_on: [E001]
blocks: [F001, F002, F003, F004, F005]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## 1. Background (背景)

用户母令（2026-10-08 23:50）三部分：
1. **停止补丁**：禁止以逐条加 prompt 替代底层能力建设
2. **审计决策**：15 个真问题必须能答（用户目标如何进入 → 谁解释 → 谁识别约束 → ...）
3. **GoalContract 12 字段**：每个用户目标进入系统必须形成机器可读的 GoalContract

**真实代码现状（2026-10-08 23:50 grep 实证）**：
- `Goal` 模型 10 字段（goal.py 4299B），`GoalContract` 0 命中
- `parse_user_goal / parse_goal / user_intent_to_goal` 全 0 命中
- `decision_audit / decision_log / decision_chain` 全 0 命中
- `DecisionAuditORM` 不存在（persistence/models.py 仅 5 ORM：Goal/Plan/Task/Trace/Evidence）
- `failure_merge / failure_cluster` 0 命中
- `cross_agent / knowledge_share` 0 命中

**Phase F 量化目标（5 卡全 Verify 后）**：
- GoalContract 12 字段全部 Pydantic schema 化（既有 5 字段扩展 + 7 字段新增）
- Alembic migration 升级/降级 双通过
- Intent Parser：rule-based + LLM hybrid，至少 5 类用户输入可解析
- Decision Audit Log：新 ORM + 持久化 + retrieve API
- Failure Pattern Merger：50 failures → ≤10 clusters，归并率 ≥70%
- GoalGuard Hook：v2 consumer 派发前校验完整率 100%

## 2. GoalContract 12 字段 Schema（Phase F 全 Verify 后状态）

| # | 字段 | 类型 | 必填 | 来源 | 备注 |
|---|------|------|------|------|------|
| 1 | stated_goal | str | ✅ | title + description | 用户原文 |
| 2 | inferred_intent | str\|None | ❌ | F002 输出 | 推断真实意图 |
| 3 | preserve_capabilities | list[str] | ✅ | metadata 升级 | 不可破坏的资产 |
| 4 | known_constraints | list[Constraint] | ✅ | budget 升级 | 含 budget/timeout/forbidden_paths |
| 5 | environment_context | EnvSnapshot | ✅ | tags 升级 | env + history |
| 6 | success_criteria | str | ✅ | 已有 | 保留 |
| 7 | failure_modes | list[FailureMode] | ✅ | **新增** | 表面成功陷阱 |
| 8 | permission_scope | PermissionScope | ✅ | **新增** | 权限范围 |
| 9 | missing_evidence | list[EvidenceRequest] | ✅ | **新增** | 缺什么证据 |
| 10 | approved_tradeoffs | list[Tradeoff] | ❌ | metadata 升级 | 用户批准的取舍 |
| 11 | autonomous_scope | list[OpType] | ✅ | **新增** | 可自主推进 |
| 12 | requires_authorization | list[OpType] | ✅ | **新增** | 需要授权 |

## 3. Decision Audit Log（新 ORM）

```sql
CREATE TABLE decision_audit (
    id UUID PRIMARY KEY,
    goal_id UUID NOT NULL REFERENCES goals(id),
    actor VARCHAR(64) NOT NULL,        -- 'codex' | 'claudecode' | 'hermes' | 'openclaw' | 'human'
    rationale TEXT NOT NULL,            -- 为什么这样决策
    alternatives TEXT[] NOT NULL,       -- 备选方案
    chosen VARCHAR(64) NOT NULL,        -- 最终选择
    outcome TEXT,                       -- 执行结果（后填）
    confidence FLOAT,                   -- 0.0-1.0
    created_at TIMESTAMP WITH TZ,
    updated_at TIMESTAMP WITH TZ
);
CREATE INDEX decision_audit_goal_id_idx ON decision_audit(goal_id);
CREATE INDEX decision_audit_actor_idx ON decision_audit(actor);
```

## 4. Failure Pattern Merger（algorithm）

- 输入：`List[FailureTrace]` (from failure_detector.py)
- 输出：`List[FailureCluster]` (根因聚合)
- 步骤：① error_message_normalize → ② embedding (hash 64-bit) → ③ cluster (DBSCAN eps=0.15) → ④ severity_score (occurrence × impact × recency) → ⑤ recommend_fix
- 验收：50 failures → ≤10 clusters, 归并率 ≥70%

## 5. GoalGuard Hook（v2 consumer 接入点）

- 接入点：`v2_consumer.py::dispatch_envelope` 调用前
- 流程：① envelope.to_goal_contract() → ② guard.validate(contract) → ③ 不通过写 risk audit envelope → ④ 通过 dispatch
- 校验：12 字段必填完整性 + failure_modes 命中检测 + permission_scope 越权检测
- 退出码：0=dispatch / 1=risk_block / 2=fatal

## 6. Phase F 验收标准（10 项判据）

- [ ] F001: Goal 模型扩展到 12 字段 + Pydantic + Alembic migration + 25+ unit tests
- [ ] F002: Intent Parser 5 类输入可解析（命令/陈述/问题/带约束/带取舍）
- [ ] F003: DecisionAuditORM + 持久化 + retrieve API
- [ ] F004: 50 failures → ≤10 clusters，归并率 ≥70%
- [ ] F005: GoalGuard Hook 在 v2 consumer 接入，0 越权
- [ ] 所有卡 preflight = 0 issues
- [ ] 12 字段全 Verify, 0 False PASS
- [ ] AGENTS.md SSOT 更新（含 Phase F 段）
- [ ] INDEX.md 全 6 卡 Verified
- [ ] _agent-hub/memory/2026-10-08.md 收尾（含 Phase F Done report 段落）

## 7. Out-of-scope（红线和 VNext 已有区分）

- ❌ 不重写 Goal/Plan/Task/Trace/Evidence 现有模型（仅扩展 Goal）
- ❌ 不动 verifier/deterministic.py（只读复用）
- ❌ 不动 v2 consumer 主循环（只增 Guard hook）
- ❌ 不写新 ad-hoc patch / 调试脚本（reports/ 下禁止 _p5v8.py 这种）
- ❌ 不动已有的 Phase A–E 49 张 Verified 卡（不可降级）
- ❌ 不在没有 evidence 的情况下写 status=Verified

## 8. Time Budget

F000 = 60 min（Codex 自写）
F001 = 90 min（GoalContract 完整化，最大）
F002 = 90 min（Intent Parser）
F003 = 60 min（Decision Audit Log 新 ORM）
F004 = 45 min（Failure Pattern Merger）
F005 = 45 min（GoalGuard Hook）
Phase F 总工程量 ~6.5h，单线程

## 9. Codex Sign-off（独立验收）

- F000 → Verified（Codex 自己签字）
- F001–F005 → 跑 `pytest tests/unit -v` + `alembic upgrade head` + preflight v4 + 抽样 grep 验证
- 全部 Verified → 写 Phase F Done report 到 memory