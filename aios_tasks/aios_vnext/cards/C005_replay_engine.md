---
id: C005
title: Replay Engine
owner: CC
priority: P0
track: 5 — VNext Phase C (Learning)
preconditions: [C004]
estimated_minutes: 120
depends_on: [C004]
blocks: [C009]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `ReplayResult` (run_id, status, duration_ms, outputs, diffs_from_expected)
2. `replay(historical_run, new_kernel)`: 用 T0033 trace 跑 historical run on new kernel
3. `diff_detect(expected, actual)`: 输出差异列表
4. 集成测试 (5 case: replay_success, replay_failure, diff_match, diff_mismatch, batch_replay)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\learning\replay_engine.py`
- `D:\AIOS\kernel\tests\integration\test_replay_engine.py`

## Out-of-scope
- ❌ Trace/Failure/Eval/Skill

## Forbidden
- ❌ protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ Replay 跟 prod 不一致

## Evidence
- [ ] replay 100 historical run
- [ ] diff detection 工作
- [ ] pytest 全 PASS

## Time Budget
120 分钟
