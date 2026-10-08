"""test_billing.py - E003."""
def test_track_event():
    from aios_kernel.product.billing import BillingTracker
    t = BillingTracker()
    t.add_credits("tenant1", 100.0)
    ev = t.track_event("tenant1", "api_call", quantity=10.0)
    assert ev.cost_usd == 0.01  # 0.001 * 10
    assert ev.credits_used == 0.01


def test_get_credits():
    from aios_kernel.product.billing import BillingTracker
    t = BillingTracker()
    assert t.get_credits("nope") == 0.0
    t.add_credits("t1", 50.0)
    assert t.get_credits("t1") == 50.0


def test_balance_calc():
    from aios_kernel.product.billing import BillingTracker
    t = BillingTracker()
    t.add_credits("t1", 100.0)
    for _ in range(10):
        t.track_event("t1", "skill_use", 1.0)  # each costs 0.10
    assert abs(t.get_credits("t1") - 99.0) < 0.01  # 100 - 10*0.10 = 0


def test_insufficient_credits():
    from aios_kernel.product.billing import BillingTracker
    t = BillingTracker()
    # No credits added
    ev = t.track_event("t1", "skill_use", 1.0)
    assert ev.credits_used == 0.0  # can't use without credits


def test_audit():
    from aios_kernel.product.billing import BillingTracker
    t = BillingTracker()
    t.add_credits("t1", 100.0)
    for _ in range(5):
        t.track_event("t1", "api_call")
    events = t.get_events("t1")
    assert len(events) == 5
