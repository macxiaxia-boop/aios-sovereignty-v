---
id: E002
title: Multi-Tenant layer
owner: CC
priority: P0
track: 7 — VNext Phase E (CloudTech)
preconditions: [E001]
estimated_minutes: 120
depends_on: [E001]
blocks: [E007]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: Tenant (id, name, tier, created_at, metadata)
2. TenantIsolation: 资源加 tenant_id
3. Repository 注入: 所有 query 加 tenant_id 过滤
4. 集成测试 (5 case: create_tenant, isolate_data, cross_tenant_query_blocked, tenant_admin_can_access, audit_cross_tenant_attempt)
