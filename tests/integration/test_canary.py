"""test_canary.py - C008 tests."""
from __future__ import annotations


def test_deploy_start():
    from aios_kernel.learning.canary import CanaryDeployer
    dep = CanaryDeployer()
    d = dep.deploy_start("skill_a", "1.0.0")
    assert d.skill_id == "skill_a"
    assert d.current_step == "shadow"
    assert d.canary_pct == 0


def test_advance_through_steps():
    from aios_kernel.learning.canary import CanaryDeployer
    dep = CanaryDeployer()
    d = dep.deploy_start("skill_b", "2.0.0")
    initial_len = len(d.history)
    dep.advance_step(d.id)
    after_first = list(d.history)
    dep.advance_step(d.id)
    after_second = list(d.history)
    assert len(after_first) == initial_len + 1
    assert len(after_second) == initial_len + 2
    pcts = [int(h["step"].rstrip("%")) for h in after_second if h["action"] == "advance_step"]
    assert pcts == sorted(pcts)


def test_auto_rollback_on_high_error_rate():
    from aios_kernel.learning.canary import CanaryDeployer
    dep = CanaryDeployer()
    d = dep.deploy_start("skill_c", "1.0.0")
    dep.advance_step(d.id)
    for _ in range(100):
        d = dep.record_call(d.id, success=False, latency_ms=100.0)
    log = dep.get_audit_log(d.id)
    assert any("rollback" in str(e).lower() for e in log) or d.current_step == "rolled_back"


def test_auto_rollback_on_slow_latency():
    from aios_kernel.learning.canary import CanaryDeployer
    dep = CanaryDeployer()
    d = dep.deploy_start("skill_d", "1.0.0", baseline_latency_ms=100.0)
    dep.advance_step(d.id)
    for _ in range(50):
        d = dep.record_call(d.id, success=True, latency_ms=1000.0)
    log = dep.get_audit_log(d.id)
    assert any("rollback" in str(e).lower() for e in log) or d.current_step == "rolled_back"


def test_audit_log():
    from aios_kernel.learning.canary import CanaryDeployer
    dep = CanaryDeployer()
    d = dep.deploy_start("skill_e", "1.0.0")
    dep.advance_step(d.id)
    dep.advance_step(d.id)
    log = dep.get_audit_log(d.id)
    assert len(log) >= 3
