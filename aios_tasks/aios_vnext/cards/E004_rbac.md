---
id: E004
title: Enterprise Permission (RBAC)
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
1. Pydantic: RBACRole (name, permissions[], tenant_id)
2. check(user, resource, action) → True/False
3. Audit log 集成
4. 集成测试 (5 case: create_role, grant_revoke, check_allow, check_deny, multi_tenant_role)
