---
id: G000
title: Phase G Acceptance Spec v0.1 — Learning Loop + Auto GoalContract Generation
owner: Codex
priority: P0
track: 7 — VNext Phase G (Learning Closure)
preconditions: [F000, F001, F002, F003, F004, F005]
estimated_minutes: 60
depends_on: [F005]
blocks: [G001, G002, G003, G004]
status: Pending
created: 2026-10-09
codex_supervisor_signoff_required: true
---

## 1. Why Phase G Exists（背景）

Phase F 建了 12 字段 GoalContract schema + Decision Audit + Intent Parser + Failure Pattern Merger + GoalGuard Hook——但**全是数据结构层，没有运行机制层**。

用户母令第 3 部分明确说"每个用户目标进入系统以后，必须形成一份机器可读的 GoalContract"——**这不是"我手动填"，是"用户输入→自动生成"**。

用户母令第 2 部分"失败经验是否改变未来行为"——**Phase F 的 Failure Merger 只归并不反哺**。归并的 cluster 没自动写回 `GoalContract.failure_modes`，所以同类失败下次还会发生。

Phase G 补齐这 3 个缺口：
1. **Failure → 反哺**（让学习闭环闭合）
2. **Inbound → GoalContract 自动生成**（每个用户目标自动有 GoalContract）
3. **Cross-agent knowledge sharing**（5 Agent 共享 failure cluster + capability index）

## 2. 验收 10 项判据

| # | 判据 |
|---|---|
| 1 | FailurePatternMerger 归并的 cluster 自动写回 GoalContract.failure_modes（每 N 分钟跑一次） |
| 2 | v2 inbound envelope 经 IntentParser 自动生成 GoalContract，无人介入 |
| 3 | 生成的 GoalContract 自动过 GoalGuard 5 类检查；不通过自动写 risk envelope |
| 4 | Cross-agent knowledge table 包含 5 Agent（codex / claudecode / hermes / openclaw / human）的 failure cluster + capability index |
| 5 | Cross-agent knowledge 在 dispatch 时被 reference（GoalGuard 可读） |
| 6 | Phase F baseline 不退化（kernel unit + v2 baseline） |
| 7 | 所有卡 preflight = 0 issues |
| 8 | AGENTS.md SSOT 更新（Phase G 段） |
| 9 | INDEX.md 全 5 卡 Verified |
| 10 | memory log 收尾（Phase G Done report） |

## 3. 复用 Phase F 资产（不重做）

- `aios_kernel.intent.parser.IntentParser` — F002
- `aios_kernel.domain.services.decision_service.DecisionService` — F003
- `aios_kernel.learning.clustering.FailurePatternMerger` — F004
- `aios_kernel.governance.goal_guard.GoalGuard` — F005
- `_agent-hub/v2/src/goal_guard_hook.py` — F005 接入点
- `_agent-hub/scripts/codex_self_audit.py` — 自主 baseline 监控

## 4. Phase G 不动红线

- ❌ 不重写 Phase A-F Verified 卡
- ❌ 不改 `kernel/alembic/versions/` migration schema（除非新字段需要）
- ❌ 不改 `verifier/deterministic.py`
- ❌ 不改 `v2_consumer.py` 主循环（最多增 hook call，不改主流程）
- ❌ 不写新 ad-hoc patch / 调试脚本
- ❌ 不在没有 evidence 的情况下写 status=Verified

## 5. Time Budget

| 卡 | 工期 | Owner |
|---|---|---|
| G000 spec | 60 min | Codex self |
| G001 Failure 反哺 | 90 min | CC dev #A |
| G002 Inbound 循环 | 120 min | CC dev #B |
| G003 Cross-agent knowledge | 90 min | CC dev #C |
| G004 verification + done | 45 min | Codex self |
| **总** | **~6.5h 单线程（3 dev 并行 ≈ 3h）** | |

## 6. 关键设计决策（Codex 监督）

### 6.1 G001 Failure 反哺
- 新增 `kernel/src/aios_kernel/learning/failure_feedback.py`
- `FailureFeedbackService.apply_clusters_to_goal(goal_id, clusters)` 把 cluster 转成 FailureMode 写回 Goal
- 新建 Scheduled Task 每 15 分钟跑：merge today's failure events → cluster → apply to active Goals
- **关键**：必须 atomic（写失败就回滚，不能部分写）

### 6.2 G002 Inbound 循环
- 新增 `_agent-hub/v2/src/inbound_goal_generation.py`
- `generate_goal_from_envelope(envelope) -> GoalContract`（v2 inbound envelope → GoalContract instance）
- 接入点：`goal_guard_hook.guard_dispatch()` 在 GoalGuard 校验前先生成 GoalContract
- **关键**：generated GoalContract 必须 cache 到 `_agent-hub/v2/state/generated_goals/` 备审计

### 6.3 G003 Cross-agent knowledge
- 新增 `_agent-hub/knowledge/cross_agent_index.py` + `kernel/src/aios_kernel/learning/cross_agent_knowledge.py`
- 数据结构：
  ```python
  class CrossAgentKnowledge(BaseModel):
      agent: str  # 'codex' | 'claudecode' | 'hermes' | 'openclaw' | 'human'
      failure_clusters: list[FailureCluster]
      capability_index: dict[str, list[str]]  # skill_id -> [use cases]
      last_updated: datetime
  ```
- 5 Agent 各有一个 CrossAgentKnowledge 实例
- GoalGuard 在 dispatch 时 reference 所有 5 Agent 的 failure cluster

## 7. 历史失败模式覆盖映射

| 用户列举失败 | Phase G 哪张卡覆盖 |
|---|---|
| AI 卸载核心工具 | G002 inbound → GoalGuard 自动拦截 |
| CloudTechAI 接口未真正可用 | G002 inbound 让每个用户请求自动有 GoalContract |
| Codex 绕开 CC 自行开发 | G003 cross-agent knowledge 让 5 Agent 看到 Codex 决策 |
| Agent 跑片刻就问是否继续 | G001 failure 反哺让 GoalContract.autonomous_scope 自动生效 |
| Skill/MCP/API 配置无系统变化 | G002 inbound 让配置变化自动被 GoalGuard 感知 |
| 改一条提示词下次又犯 | G001 failure 反哺让 FailureMode 写回 GoalContract → GoalGuard 检测 |
| 用户目标如何进入 AIOS | G002 inbound 通用循环 |
| 哪个组件识别隐含约束 | G002 IntentParser + GoalContract.known_constraints |
| AIOS 是否分类目标 | G002 IntentType classifier |
| 是否发现已有工具 | G003 capability_index |
| 方案执行前是否评估后果 | G002 + G003 GoalGuard pre-dispatch + cross-agent reference |
| AI 判断方案正确的依据 | G001 + G003 FailureMode + CrossAgentKnowledge.rationale |
| 失败记录在哪里 | F003 已建，Phase G 不重做 |
| 同类失败是否归并 | F004 已建，**G001 加反哺** |
| **失败经验是否改变未来行为** | **G001 核心（反哺到 GoalContract）** |
| **新行为有没有在陌生任务验证** | **G003 跨 Agent reference** |
| **不同 Agent 用相同经验** | **G003 核心** |

---

**G000 Sign-off**: Codex 2026-10-09 09:50 Verified.