"""test_multi_tenant.py - E002."""
def test_create_tenant():
    from aios_kernel.product.multi_tenant import TenantRegistry
    r = TenantRegistry()
    t = r.create_tenant("acme", "free")
    assert t.tier == "free"
    assert r.get_tenant(str(t.id)) is not None


def test_isolation_log():
    from aios_kernel.product.multi_tenant import TenantRegistry
    r = TenantRegistry()
    t = r.create_tenant("acme")
    iso = r.check_isolation(str(t.id), "res-1", "goal")
    assert iso.access_granted is True
    log = r.get_isolation_log(str(t.id))
    assert len(log) == 1


def test_unknown_tenant_returns_none():
    from aios_kernel.product.multi_tenant import TenantRegistry
    r = TenantRegistry()
    assert r.get_tenant("nope") is None


def test_tenant_tier_validation():
    from aios_kernel.product.multi_tenant import TenantRegistry
    r = TenantRegistry()
    t = r.create_tenant("big", "enterprise")
    assert t.tier == "enterprise"


def test_isolation_default_allowed():
    from aios_kernel.product.multi_tenant import TenantRegistry
    r = TenantRegistry()
    t = r.create_tenant("x")
    iso = r.check_isolation(str(t.id), "r", "task")
    assert iso.access_granted is True
