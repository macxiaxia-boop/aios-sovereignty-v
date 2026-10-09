---
id: C008
title: Skill Canary Mechanism
owner: CC
priority: P0
track: 5 — VNext Phase C (Learning)
preconditions: [C006]
estimated_minutes: 120
depends_on: [C006]
blocks: [C009]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `CanaryDeployment` (id, skill_id, version, started_at, canary_pct, current_step, metric)
2. 5-step canary: shadow → 5% → 25% → 50% → 100%
3. Auto-rollback on error_rate > 1% or latency > 2x baseline
5. 集成测试 (5 case: deploy_start, advance_step, auto_rollback, full_promotion, audit)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\learning\canary.py`
- `D:\AIOS\kernel\tests\integration\test_canary.py`

## Out-of-scope
- ❌ Deprecation (C007)
- ❌ Eval/Replay (C004/C005)

## Forbidden
- ❌ protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ 跳 canary (full deploy 没用 canary)

## Evidence
- [ ] new skill 灰度 5% → monitor → promote 100%
- [ ] auto-rollback on threshold
- [ ] pytest 全 PASS

## Time Budget
120 分钟
