---
id: D005
title: Marketing Feedback + Skill recommendation
owner: CC
priority: P0
track: 6 — VNext Phase D (Business)
preconditions: [D004]
estimated_minutes: 90
depends_on: [D004]
blocks: [D007]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `MarketingCampaign` (id, name, channel, impressions, conversions, cost, roi, skill_id)
2. `track_campaign(campaign)`: track ROI metrics
3. `recommend_skill_promotion(campaign)`: 高 ROI campaign → 物化为 skill
4. 集成测试 (5 case: track_basic, roi_calc, skill_recommendation, low_roi_skip, audit)

## Evidence
- [ ] 100 campaigns tracked
- [ ] ROI 正确计算
- [ ] skill_recommendation when ROI > threshold
- [ ] pytest 全 PASS
