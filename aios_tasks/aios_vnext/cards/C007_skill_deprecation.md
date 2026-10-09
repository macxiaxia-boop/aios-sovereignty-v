---
id: C007
title: Skill Deprecation (auto-detect unused)
owner: CC
priority: P0
track: 5 — VNext Phase C (Learning)
preconditions: [C006]
estimated_minutes: 60
depends_on: [C006]
blocks: [C008, C009]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `Deprecation` (skill_id, unused_days, last_used_at, reason)
2. `detect_deprecated(skill_registry, unused_days=30)`: 自动检测 unused skill
3. 标记 deprecated_at + 推荐 successor
4. 集成测试 (5 case: detect_old_unused, detect_recent_unused, deprecate_recommendation, audit_log, format)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\learning\skill_deprecation.py`
- `D:\AIOS\kernel\tests\integration\test_skill_deprecation.py`

## Out-of-scope
- ❌ Skill Usage (C006)
- ❌ Canary (C008)

## Forbidden
- ❌ protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ 静默 deprecate (无 audit)

## Evidence
- [ ] unused 30 days 100% 自动检测
- [ ] audit log 全数保留
- [ ] pytest 全 PASS

## Time Budget
60 分钟
