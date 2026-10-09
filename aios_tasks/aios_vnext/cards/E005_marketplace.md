---
id: E005
title: Workflow Marketplace
owner: CC
priority: P0
track: 7 — VNext Phase E (CloudTech)
preconditions: [E003, E004]
estimated_minutes: 90
depends_on: [E003, E004]
blocks: [E007]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: MarketplaceListing (skill_id, seller_tenant_id, price_usd, sales_count, rating)
2. list_skill(skill_id, price, seller): MarketplaceListing
3. purchase_skill(buyer_tenant_id, listing) → transfer credits
4. 集成测试 (5 case: list, purchase, rating, revenue_split, audit)
