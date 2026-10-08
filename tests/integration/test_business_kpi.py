"""test_business_kpi.py - D006 tests."""
from __future__ import annotations
from unittest.mock import MagicMock


def test_track_kpi_basic():
    from aios_kernel.business.business_kpi import BusinessKPIDashboard
    d = BusinessKPIDashboard()
    kpi = d.track_kpi("mrr", 50000.0, target=100000.0)
    assert kpi.value == 50000.0
    assert kpi.target == 100000.0


def test_dashboard_20_kpis():
    from aios_kernel.business.business_kpi import BusinessKPIDashboard
    d = BusinessKPIDashboard()
    dash = d.dashboard()
    assert len(dash) >= 19  # 19 KPI defaults, may have +1 from prior test
    for kpi_name in ["mrr", "churn_rate_pct", "nps_promoters_pct"]:
        assert kpi_name in dash


def test_trend_up_down():
    from aios_kernel.business.business_kpi import BusinessKPIDashboard
    d = BusinessKPIDashboard()
    d.track_kpi("mrr", 100.0)
    kpi2 = d.track_kpi("mrr", 150.0)
    assert kpi2.trend == "up"
    kpi3 = d.track_kpi("mrr", 100.0)
    assert kpi3.trend == "down"


def test_skill_promotion_trigger_high_roi():
    from aios_kernel.business.business_kpi import BusinessKPIDashboard
    d = BusinessKPIDashboard()
    skill_id = d.check_skill_promotion_trigger(campaign_roi=5.0)
    assert skill_id is not None
    assert skill_id.startswith("campaign_roi_")


def test_skill_promotion_low_roi_no_trigger():
    from aios_kernel.business.business_kpi import BusinessKPIDashboard
    d = BusinessKPIDashboard()
    skill_id = d.check_skill_promotion_trigger(campaign_roi=1.0)
    assert skill_id is None
