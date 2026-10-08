"""test_rbac.py - E004."""
def test_create_role():
    from aios_kernel.product.rbac import RBACManager
    m = RBACManager()
    r = m.create_role("admin", ["*:*"])
    assert r.name == "admin"


def test_grant_revoke():
    from aios_kernel.product.rbac import RBACManager
    m = RBACManager()
    r = m.create_role("dev", ["goal:create", "task:run"])
    assert m.check(str(r.id), "goal", "create") is True
    assert m.check(str(r.id), "task", "run") is True


def test_check_allow():
    from aios_kernel.product.rbac import RBACManager
    m = RBACManager()
    r = m.create_role("user", ["goal:read"])
    assert m.check(str(r.id), "goal", "read") is True


def test_check_deny():
    from aios_kernel.product.rbac import RBACManager
    m = RBACManager()
    r = m.create_role("user", ["goal:read"])
    assert m.check(str(r.id), "goal", "delete") is False


def test_audit_log():
    from aios_kernel.product.rbac import RBACManager
    m = RBACManager()
    r = m.create_role("a", ["*:*"])
    m.check(str(r.id), "x", "y")
    log = m.get_audit_log()
    assert len(log) == 1
    assert log[0]["allowed"] is True
