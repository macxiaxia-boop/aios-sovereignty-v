---
id: E003
title: Billing & Credits tracking
owner: CC
priority: P0
track: 7 — VNext Phase E (CloudTech)
preconditions: [E002]
estimated_minutes: 90
depends_on: [E002]
blocks: [E007]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: BillingEvent (tenant_id, event_type, quantity, cost_usd, credits_used, stripe_charge_id)
2. track_event(tenant_id, event_type, quantity) → BillingEvent
3. Credits balance per tenant
4. Stripe integration mock (no real API)
5. 集成测试 (5 case: track_single, balance_calc, credits_sufficient, overage, audit)
