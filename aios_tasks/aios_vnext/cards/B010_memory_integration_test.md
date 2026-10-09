---
id: B010
title: Memory + Context integration test (100-task with memory recall)
owner: CC
priority: P0
track: 4 — VNext Phase B (Context)
preconditions: [B002, B003, B004]
estimated_minutes: 180
depends_on: [B002, B003, B004]
blocks: [B012]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. 复用 T0036 100-task 闭环
2. **扩展每 Task**:
   - Before execute: ContextCompiler.compile(task) → 注入 Context
   - After complete: Task 写入 LongTermMemory (含 source_evidence_id back-link)
   - 跨 Task: Working Memory 记录 task 之间的中间状态
3. **集成测试** (5 case):
   - 100-task 全部 PASS (复用 T0036)
   - Memory recall: task 51 引用 task 1 的 evidence
   - Working Memory session-isolation
   - Long-term Memory retention >= 30 days
   - Context Compiler token ≤ 4096/task

## 路径
- `D:\AIOS\kernel\tests\integration\test_memory_context_integration.py`

## Forbidden
- ❌ 触碰 T0036 已 Verified 内容
- ❌ 触碰 T0030-T0040 已 Verified
- ❌ 触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Evidence Requirements
- [ ] 100-task 全部 PASS
- [ ] Memory recall 工作 (task 51 → task 1)
- [ ] Long-term Memory 30-day retention
- [ ] pytest 全 PASS
- [ ] preflight CLEAN

## Exit Criteria
1. evidence 全勾
2. pytest exit 0
3. status=Submitted

## Time Budget
180 分钟
