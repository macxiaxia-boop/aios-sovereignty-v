---
id: C002
title: Trace Mining layer
owner: CC
priority: P0
track: 5 — VNext Phase C (Learning)
preconditions: [C001]
estimated_minutes: 120
depends_on: [C001]
blocks: [C003, C006]
status: Pending
created: 2026-10-08
---

## Scope (要做)
1. Pydantic: `TracePattern` (id, pattern_type, description, frequency, first_seen, last_seen, example_trace_ids)
2. Read T0033 traces from `traces` table (real execution history)
3. 算法: 按 event_type 分类 success/failure → 提取 pattern
4. 集成测试 (5 case: extract success patterns, extract failure patterns, dedup, time_range filter, format)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\learning\trace_miner.py`
- `D:\AIOS\kernel\tests\integration\test_trace_miner.py`

## Out-of-scope
- ❌ Failure Pattern Detector (C003)
- ❌ Eval Dataset (C004)
- ❌ Replay Engine (C005)
- ❌ Skill Evolution (C006-C008)
- ❌ 触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）
- ❌ 触碰 `_archived/`, `_backups/` 等

## Forbidden
- ❌ protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ over-extract (无意义 patterns)

## Evidence
- [ ] 100 真实 trace 提取 ≥ 80 patterns
- [ ] success/failure 分类准确
- [ ] pytest 全 PASS
- [ ] preflight CLEAN

## Time Budget
120 分钟
