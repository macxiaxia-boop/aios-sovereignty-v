---
id: C006
title: Skill Usage Tracker
owner: CC
priority: P0
track: 5 — VNext Phase C (Learning)
preconditions: [C002]
estimated_minutes: 90
depends_on: [C002]
blocks: [C007, C008]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `SkillUsage` (skill_id, used_at, success_count, failure_count, context_hash)
2. `track(skill_id, success)`: 每次 skill 调用记录
3. `get_usage(skill_id, since)`: 查询使用情况
4. 集成测试 (5 case: track_basic, get_usage_time_range, success_rate, deprecate_candidate, format)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\learning\skill_usage.py`
- `D:\AIOS\kernel\tests\integration\test_skill_usage.py`

## Out-of-scope
- ❌ Deprecation (C007)
- ❌ Canary (C008)

## Forbidden
- ❌ protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ 静默 track (无 audit log)

## Evidence
- [ ] 5 skills × 100 task = 500 calls 全数 captured
- [ ] time-range filter
- [ ] pytest 全 PASS

## Time Budget
90 分钟
