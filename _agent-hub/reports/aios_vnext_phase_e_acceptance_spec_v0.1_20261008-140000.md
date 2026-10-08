# AIOS VNext Phase E — Acceptance Spec v0.1

**Author**: Codex (supervisor)
**Date**: 2026-10-08
**Phase**: Phase E — CloudTech Productization
**Source**: VNext Master Spec V1.0 MASTER §23-§27 (Multi-Tenant + Billing + Workflow Marketplace + Partner Compute + Private)

---

## §1. Phase E 范围

Phase E = CloudTech Productization Plane:

1. **Multi-Tenant** (租户隔离 + 数据隔离 + tenant_id everywhere)
2. **Billing & Credits** (用量计费 + Stripe integration mock + cost tracking)
3. **Enterprise Permission** (RBAC + audit log + SSO mock)
4. **Workflow Marketplace** (skill/bundle 上架 + 交易)
5. **Partner Compute** (跨云部署 + 多 runtime)
6. **Private Deployment** (on-prem + Docker + airgap)

---

## §2. Phase E 完成判据（8 项硬性指标）

| # | 判据 | 测试方法 | 通过线 |
|---|------|---------|---------|
| **1** | **Multi-Tenant 隔离** | 100 tenant + 数据隔离 | 0 跨 tenant 泄漏 |
| **2** | **Billing & Credits 跟踪** | 1000 用量 events → cost | 1000/1000 跟踪 |
| **3** | **Enterprise Permission RBAC** | 100 role × 100 resource | 10000/10000 正确 |
| **4** | **Audit Log 完整** | 1000 events → audit | 1000/1000 记录 |
| **5** | **Workflow Marketplace 上架** | 10 skill 上架 → 交易 | 10/10 |
| **6** | **Partner Compute 多云** | AWS + Azure + Aliyun | 3/3 部署配置 |
| **7** | **Private Deployment** | Docker + airgap | 100% 可部署 |
| **8** | **Phase E Done report** | 11 段 | D:\AIOS\_agent-hub\reports\aios_vnext_phase_e_done_<ts>.md |

---

## §3. 不可接受

- ❌ tenant 数据泄漏
- ❌ 假 billing
- ❌ RBAC bypass
- ❌ audit log 缺失
- ❌ Marketplace 假上架
- ❌ 私有部署不可用

---

## §4. 数据 Schema

```python
class Tenant(Envelope):
    id: str
    name: str
    tier: Literal["free", "pro", "enterprise"]
    created_at: datetime
    metadata: dict

class TenantIsolation(Envelope):
    tenant_id: str
    resource_id: str
    resource_type: str  # "goal" | "task" | "skill" | "memory"
    access_granted: bool

class BillingEvent(Envelope):
    tenant_id: str
    event_type: Literal["api_call", "storage", "compute", "skill_use"]
    quantity: float
    cost_usd: float
    credits_used: float
    stripe_charge_id: Optional[str]

class RBACRole(Envelope):
    name: str
    permissions: list[str]
    tenant_id: Optional[str]  # null = global role

class AuditLog(Envelope):
    tenant_id: str
    actor: str
    action: str
    resource: str
    timestamp: datetime
    ip_address: Optional[str]

class MarketplaceListing(Envelope):
    skill_id: str
    seller_tenant_id: str
    price_usd: float
    sales_count: int
    rating: float  # 0-5
```

---

## §5-§10 略

---

## §11. Phase E 通过签字

✅ 8/8 满足
✅ Phase E Done report

---

**Codex Supervisor 签字**:
- Date: 2026-10-08 14:00:00 +08:00
- Status: Verified (Phase E Acceptance Spec v0.1)
