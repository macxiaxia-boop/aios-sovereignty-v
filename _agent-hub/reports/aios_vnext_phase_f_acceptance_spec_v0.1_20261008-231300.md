# Phase F Acceptance Spec v0.1 — Cognitive Governance Plane

> **Issued by**: Codex (supervisor) — 2026-10-08 23:12
> **Status**: Verified (Codex self-verified at 23:13 +08:00)
> **Authority**: AGENTS.md (`D:\AIOS\_agent-hub\AGENTS.md`) + 用户母令 2026-10-08 23:50
> **Linked INDEX**: `D:\AIOS\aios_tasks\aios_vnext\INDEX.md` v5 §Phase F
> **Scope**: 5 CC cards + 1 Codex self card

---

## 1. Why Phase F Exists (背景)

用户母令 23:50 三部分清晰：
1. **停止补丁模式** —— 禁止以逐条加 prompt 替代底层能力建设
2. **审计决策链路** —— 15 个真问题必须能答
3. **GoalContract 12 字段** —— 每个用户目标进入系统必须形成机器可读的 GoalContract

历史失败模式（用户列举）：
- AI 卸载核心工具（性能优化越界）
- CloudTechAI 接口未真正可用
- Codex 绕开 CC 自行开发
- Agent 跑片刻就问"是否继续"
- Skills/MCP/API/Agent 配一堆，系统无对应变化
- 改一条提示词，下次又犯同类错误

Phase A–E 已建（49/51 Verified）但**不覆盖认知治理层**。

## 2. GoalContract 12 字段 Schema（Phase F 终态）

| # | 字段 | 类型 | 必填 | 来源 | 备注 |
|---|------|------|------|------|------|
| 1 | stated_goal | str | ✅ | title + description | 用户原文 |
| 2 | inferred_intent | str \| None | ❌ | F002 输出 | 推断真实意图 |
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

子模型（7 个新 Pydantic BaseModel）：
- `Constraint` (type/value/rationale) — Literal["budget", "timeout", "forbidden_path", "rate_limit", "scope"]
- `EnvSnapshot` (cwd/os/available_tools/recent_failures/history_refs)
- `FailureMode` (description/detection/indicator)
- `PermissionScope` (allowed_paths/allowed_ops/max_budget/max_duration_sec/requires_approval)
- `EvidenceRequest` (description/source/required)
- `Tradeoff` (decision/cost/benefit/approved_by)
- `OpType` (domain/action/target) — Literal["file", "network", "service", "data", "config"] × Literal["read", "write", "execute", "delete", "modify"]

## 3. Decision Audit Log（新 ORM）

```sql
CREATE TABLE decision_audit (
    id UUID PRIMARY KEY,
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    actor VARCHAR(64) NOT NULL,        -- 'codex' | 'claudecode' | 'hermes' | 'openclaw' | 'human' | 'system'
    rationale TEXT NOT NULL,            -- 为什么这样决策
    alternatives JSON NOT NULL DEFAULT '[]',  -- 备选方案
    chosen VARCHAR(64) NOT NULL,        -- 最终选择
    outcome VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending/succeeded/failed/blocked
    outcome_detail TEXT,
    confidence FLOAT NOT NULL DEFAULT 1.0,  -- 0.0-1.0
    tags JSON NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX decision_audit_goal_id_idx ON decision_audit(goal_id);
CREATE INDEX decision_audit_actor_idx ON decision_audit(actor);
CREATE INDEX decision_audit_outcome_idx ON decision_audit(outcome);
```

## 4. Failure Pattern Merger（algorithm）

- 输入：`List[FailureTrace]` (id, error_message, error_type, context, timestamp)
- 输出：`List[FailureCluster]` (cluster_id, root_cause, error_type, affected_trace_ids, occurrence_count, severity_score, first_seen, last_seen, recommended_fix, sample_error_messages)
- 步骤：
  1. **normalize**：error_message 去除路径/IP/数字/UUID/timestamp → `<PATH>` / `<IP>` / `<NUM>` / `<UUID>` / `<TS>`
  2. **hash**：SHA256(normalized) → 16 hex chars
  3. **cluster**：同 hash = 同 cluster
  4. **severity_score** = min(10.0, occurrence_count × impact)
  5. **root_cause**：启发式 5 类（permission_denied / file_missing / timeout / network_unavailable / input_invalid / unknown）
  6. **recommend_fix**：每类根因对应修复建议
- 验收：50 failures → ≤10 clusters, 归并率 ≥70%

## 5. GoalGuard Hook（v2 consumer 接入点）

- 接入点：`v2_consumer.py::dispatch_envelope` 调用前
- 流程：
  1. `envelope.to_goal_contract()` → 加载 Goal
  2. `guard.validate(contract)` → 5 类检查
  3. 不通过 → 写 risk envelope 到 `v2/messages/risk/` + 不 dispatch
  4. 通过 → 既有 dispatch 流程
- 5 类检查：
  1. **必填字段完整性**：10 字段（title/success_criteria/budget/owner/status/permission_scope/failure_modes/missing_evidence/autonomous_scope/requires_authorization）非空
  2. **失败陷阱**：failure_modes 非空
  3. **权限越权**：allowed_paths 不覆盖 verifier/AGENTS.md
  4. **作用域不重叠**：autonomous_scope ∩ requires_authorization = ∅
  5. **缺失证据有采集计划**：missing_evidence 含 required=True 项
- 退出码：
  - `PASS`：dispatch
  - `RISK_BLOCK`：写 risk envelope, 不 dispatch
  - `FATAL`：直接隔离 envelope, 写 risk envelope

## 6. Phase F 验收 10 项判据（Codex 独立验收）

1. **F001**：Goal 模型扩展到 12 字段 + Pydantic + Alembic migration 002 + 25+ unit tests PASS
2. **F002**：Intent Parser 5 类输入可解析（命令/陈述/问题/带约束/带取舍），≥15 case PASS
3. **F003**：DecisionAuditORM + 持久化 + retrieve API，20+ case PASS
4. **F004**：50 failures → ≤10 clusters, 归并率 ≥70%
5. **F005**：GoalGuard Hook 在 v2 consumer 接入（diff ≤ 10 行），0 越权，15+ case PASS
6. **所有卡 preflight = 0 issues**
7. **12 字段全 Verify, 0 False PASS**
8. **AGENTS.md SSOT 更新**（含 Phase F 段）
9. **INDEX.md 全 6 卡 Verified**
10. **_agent-hub/memory/2026-10-08.md 收尾**（含 Phase F Done report 段落）

## 7. Out-of-scope（红线）

- ❌ 不重写 Goal/Plan/Task/Trace/Evidence 现有模型（仅扩展 Goal）
- ❌ 不动 verifier/deterministic.py（只读复用）
- ❌ 不动 v2 consumer 主循环（只增 Guard hook, diff ≤ 10 行）
- ❌ 不写新 ad-hoc patch / 调试脚本
- ❌ 不动已有的 Phase A–E 49 张 Verified 卡（不可降级）
- ❌ 不在没有 evidence 的情况下写 status=Verified

## 8. Time Budget

| 卡 | 工期 | 累计 |
|----|------|------|
| F000 (Codex self) | 60 min | 60 min |
| F001 (CC dev #A) | 90 min | 150 min |
| F002 (CC dev #B) | 90 min | 240 min |
| F003 (CC dev #C) | 60 min | 300 min |
| F004 (CC dev #D) | 45 min | 345 min |
| F005 (CC dev #E) | 45 min | 390 min |
| **Phase F 总** | **~6.5h 单线程** | |

## 9. Codex Sign-off（独立验收步骤）

1. F000 → Verified（Codex 自己写、自己验、立刻签字）
2. F001–F005 → 等 dev 报告 → 跑 `pytest tests/unit -v` + `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` + preflight v4 + 抽样 grep 验证
3. 全部 Verified → 写 Phase F Done report 到 `D:\AIOS\_agent-hub\memory\2026-10-08.md`
4. 更新 AGENTS.md SSOT（含 Phase F 段）
5. 更新 INDEX.md 全 6 卡 Verified

## 10. 历史失败模式覆盖映射

| 用户列举的失败 | Phase F 哪张卡覆盖 |
|---|---|
| AI 卸载核心工具（性能优化越界） | F005 GoalGuard permission_scope 越权检测 |
| CloudTechAI 接口未真正可用 | F005 GoalGuard failure_modes 表面成功陷阱检测 |
| Codex 绕开 CC 自行开发 | F003 Decision Audit actor 字段 |
| Agent 跑片刻就问"是否继续" | F001 GoalContract autonomous_scope vs requires_authorization |
| Skills/MCP/API/Agent 配一堆无系统变化 | F005 GoalGuard Hook 强制 GoalContract 12 字段 |
| 改一条提示词下次又犯同类错误 | F004 Failure Pattern Merger 归并同源失败 |
| 用户目标如何进入 AIOS | F002 Intent Parser（用户文本 → GoalContract） |
| 哪个组件识别用户隐含约束 | F001 known_constraints |
| AIOS 是否分类目标 | F002 IntentType classifier |
| 是否发现自己拥有工具 | F001 preserve_capabilities |
| 任务交给哪个 Agent | F003 Decision Audit actor |
| 方案执行前是否评估后果 | F001 failure_modes |
| AI 判断方案正确的依据 | F003 Decision Audit rationale + alternatives + confidence |
| 谁负责独立验收 | F005 GoalGuard + 既有 verifier/deterministic.py |
| 失败记录在哪里 | F004 Failure Pattern Merger + 既有 failure_detector.py |
| 同类失败是否归并 | F004 Failure Pattern Merger |
| 失败经验是否改变未来行为 | F004 → F005 feedback loop（clusters → GoalContract.failure_modes → Guard check） |
| 不同 Agent 用相同经验 | F001 preserve_capabilities（shared 资产清单）|

---

**F000 Sign-off**: Codex 2026-10-08 23:13 Verified.