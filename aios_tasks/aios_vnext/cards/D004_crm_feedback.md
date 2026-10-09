---
id: D004
title: CRM Feedback ingestion
owner: CC
priority: P0
track: 6 — VNext Phase D (Business)
preconditions: [D002]
estimated_minutes: 90
depends_on: [D002]
blocks: [D005, D007]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `CRMEvent` (id, customer_id_hash, event_type 5枚举, severity, product, action_recommended)
2. `ingest_event(event_dict)`: 接收 + hash customer_id
3. `categorize(events)`: 5 categories (churn/upsell/support/feedback/purchase)
4. 集成测试 (5 case: ingest_single, hash_customer_id, categorize_correct, privacy_already_500, audit)

## Evidence
- [ ] 1000 customer events → 1000/1000 ingested
- [ ] customer_id 必 hash (PII 脱敏)
- [ ] categorize 5 类全数
- [ ] pytest 全 PASS
