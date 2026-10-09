---
id: D002
title: Industry Scout
owner: CC
priority: P0
track: 6 — VNext Phase D (Business)
preconditions: [D001]
estimated_minutes: 90
depends_on: [D001]
blocks: [D007]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `IndustrySignal` (id, source, category 5枚举, title, content, url, confidence 0-1, action_required)
2. `collect(sources)`: 多 RSS / API / manual source 收信号
3. `classify(signal)`: 5 categories (product/competitor/regulatory/market/tech)
4. `alert(signal, threshold)`: confidence > threshold trigger
5. 集成测试 (5 case: collect_empty, classify_correct, alert_triggered, alert_skipped, dedup)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\business\industry_scout.py`
- `D:\AIOS\kernel\tests\integration\test_industry_scout.py`

## Out-of-scope
- ❌ Experiment Engine (D003)
- ❌ CRM/Marketing/KPI

## Forbidden
- ❌ protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ 真实外部 API 调用 (用 mock sources)
- ❌ 触碰 `D:\AIOS\aios_tasks\aios_vnext\*` (除 evidence)

## Evidence
- [ ] 100 signals → 100/100 classified
- [ ] alert threshold 工作
- [ ] dedup
- [ ] pytest 全 PASS
- [ ] preflight CLEAN

## Time Budget
90 分钟
