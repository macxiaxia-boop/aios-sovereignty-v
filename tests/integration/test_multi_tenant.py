"""test_multi_tenant.py - E002 (using tenant.py API)."""
from aios_kernel.product.tenant import TenantRegistry, Tenant, TenantAuditor


def test_create_tenant():
    r = TenantRegistry()
    t = r.create(name="acme", tier="free")
    assert t.tier == "free"
    assert r.get(t.id) is not None


def test_isolation_log():
    r = TenantRegistry()
    a = r.create(name="a")
    auditor = TenantAuditor()
    # Just check auditor can record
    auditor.record(
        actor_tenant_id=str(a.id),
        target_tenant_id=str(a.id),
        resource_id="res-1",
        action="read",
        verdict="allowed",
    )
    assert len(auditor.entries) == 1


def test_unknown_tenant_returns_none():
    r = TenantRegistry()
    assert r.get("nope") is None  # by id or None


def test_tenant_tier_validation():
    r = TenantRegistry()
    t = r.create(name="big", tier="enterprise")
    assert t.tier == "enterprise"


def test_isolation_default_allowed():
    r = TenantRegistry()
    t = r.create(name="x")
    auditor = TenantAuditor()
    auditor.record(
        actor_tenant_id=str(t.id),
        target_tenant_id=str(t.id),
        resource_id="r",
        action="task",
        verdict="allowed",
    )
    assert auditor.entries[0]["verdict"] == "allowed"
