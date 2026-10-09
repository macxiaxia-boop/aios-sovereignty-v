---
id: G004
title: Phase G Verification + Done Report
owner: Codex
priority: P0
track: 7 — VNext Phase G (Learning Closure)
preconditions: [G001, G002, G003]
estimated_minutes: 45
depends_on: [G001, G002, G003]
blocks: []
status: Pending
created: 2026-10-09
codex_supervisor_signoff_required: true
---

## Scope (要做)

Codex supervisor 独立验收 G001/G002/G003，写 Phase G Done report。

## Codex 验收步骤

### 1. G001 验收
1. `cd D:\AIOS\kernel && python -m pytest tests/unit/test_failure_feedback.py -v` 20+ case PASS
2. `python -m aios_kernel.learning.failure_feedback_runner --min-occurrence 3` 实际跑一次输出 results
3. `git diff kernel/src/aios_kernel/learning/` 改 + 不增不改

### 2. G002 验收
1. `cd D:\AIOS\_agent-hub\v2 && python -m pytest tests/test_inbound_goal_generation.py -v` 15+ PASS
2. `git diff _agent-hub/v2/src/goal_guard_hook.py` 行数 ≤ 10
3. 手动测试 1 个 generic envelope → cache 文件验证

### 3. G003 验收
1. `cd D:\AIOS\kernel && python -m pytest tests/unit/test_cross_agent_knowledge.py -v` 15+ PASS
2. 5 agent JSON 文件存在
3. GoalGuard validate() 不报错

### 4. Phase G 综合验收
1. `pytest kernel/tests/unit -v` 全套仍 PASS
2. `pytest _agent-hub/v2/tests/ -v` 既有 baseline 不退化
3. `python D:\AIOS\_agent-hub\scripts\codex_self_audit.py` → OVERALL: CLEAN (exit=0)
4. preflight v4 = 0 issues

### 5. Done Report
- 路径: `D:\AIOS\_agent-hub\reports\aios_vnext_phase_g_done_20261009.md`
- 必含：
  - 5 张卡状态表
  - 验收 10 项判据结果
  - 历史失败模式覆盖映射（用户母令列举 → Phase G 哪张卡）
  - 文件清单
  - Codex Sign-off

### 6. AGENTS.md SSOT 更新
- 追加 Phase G 段
- Phase G 强制新增红线：
  - ❌ 不重写 Phase A-F Verified 卡
  - ❌ 不绕开 GoalGuard dispatch

### 8. INDEX.md 更新
- 5 张 Phase G 卡 status=Verified

### 9. memory log 收尾
- `_agent-hub/memory/2026-10-09.md` 末尾追加 Phase G Done report 段

## 验收 10 项判据（必须全过）

| # | 判据 | 验收方法 |
|---|---|---|
| 1 | FailurePatternMerger cluster 自动写回 GoalContract.failure_modes | G001 tests PASS + runner 输出 results |
| 2 | v2 inbound → GoalContract 自动生成 | G002 tests PASS |
| 3 | GoalContract 自动 GoalGuard 校验 | G002 process_inbound_envelope 集成 |
| 4 | Cross-agent knowledge 5 Agent | G003 load_all() 返回 5 |
| 5 | Cross-agent knowledge 在 dispatch 被 reference | G003 GoalGuard integration |
| 6 | Phase F baseline 不退化 | kernel unit + v2 baseline PASS |
| 7 | 所有 preflight = 0 issues | codex supervisor 跑 |
| 8 | AGENTS.md SSOT 更新 | 手动验证 |
| 9 | INDEX.md 5 卡 Verified | 手动验证 |
| 10 | memory log 收尾 | 手动验证 |

## Out-of-scope

- ❌ 不重新验收 Phase A-F
- ❌ 不实现 G001-G003 之外的任何新功能
- ❌ 不改 self-audit script（Phase F 已建）
- ❌ 不写新 ad-hoc patch / 调试脚本

## Time Budget

45 分钟

## Codex Sign-off

10/10 判据全过 + 全部 baseline 不退化 → status=Verified → 写 Done report → 更新 SSOT → 更新 INDEX → 更新 memory。