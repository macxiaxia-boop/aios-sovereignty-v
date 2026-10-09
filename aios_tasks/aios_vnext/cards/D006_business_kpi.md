---
id: D006
title: Business Outcome KPI dashboard
owner: CC
priority: P0
track: 6 — VNext Phase D (Business)
preconditions: [D003, D005]
estimated_minutes: 60
depends_on: [D003, D005]
blocks: [D007]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `BusinessKPI` (id, name, value, target, trend, freshness 0-1)
2. `track_kpi(name, value)`: 跟踪单个 KPI
3. `dashboard()`: 20 KPI 实时 dashboard
4. D→C 闭环: outcome → skill promotion 触发
5. 集成测试 (5 case: track_kpi, dashboard_fresh, trend_up_down, skill_promotion_trigger, audit)

## Evidence
- [ ] 20 KPI dashboard 实时
- [ ] ≥ 95% freshness
- [ ] D→C 闭环 1 case 验证
- [ ] pytest 全 PASS
