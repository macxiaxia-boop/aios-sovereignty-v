"""business_kpi.py - D006 Business Outcome KPI dashboard."""
from __future__ import annotations
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow


class BusinessKPI(Envelope):
    name: str
    value: float = 0.0
    target: float = 0.0
    trend: str = "stable"
    freshness: float = 1.0
    last_updated: Optional[datetime] = None


class BusinessKPIDashboard:
    def __init__(self):
        self._kpis: dict[str, BusinessKPI] = {}

    def track_kpi(self, name: str, value: float, target: float = 0.0) -> BusinessKPI:
        existing = self._kpis.get(name)
        trend = "stable"
        if existing is not None:
            if value > existing.value:
                trend = "up"
            elif value < existing.value:
                trend = "down"
        kpi = BusinessKPI(
            id=str(uuid.uuid4()),
            name=name,
            value=value,
            target=target,
            trend=trend,
            freshness=1.0,
            last_updated=utcnow(),
        )
        self._kpis[name] = kpi
        return kpi

    def dashboard(self) -> dict:
        defaults = [
            ("mrr", 0.0, 100000.0), ("arr", 0.0, 1200000.0),
            ("active_customers", 0.0, 1000.0), ("new_signups_monthly", 0.0, 100.0),
            ("churn_rate_pct", 0.0, 5.0), ("net_promoter_score", 0.0, 50.0),
            ("customer_acquisition_cost", 0.0, 100.0), ("lifetime_value", 0.0, 5000.0),
            ("daily_active_users", 0.0, 500.0), ("monthly_active_users", 0.0, 2000.0),
            ("api_calls_per_day", 0.0, 100000.0), ("error_rate_pct", 0.0, 1.0),
            ("p95_latency_ms", 0.0, 200.0), ("uptime_pct", 0.0, 99.9),
            ("gross_margin_pct", 0.0, 70.0), ("conversion_rate_pct", 0.0, 5.0),
            ("trial_to_paid_pct", 0.0, 25.0), ("support_tickets_per_day", 0.0, 50.0),
            ("nps_promoters_pct", 0.0, 60.0),
        ]
        for name, value, target in defaults:
            if name not in self._kpis:
                self.track_kpi(name, value, target)
        return {name: kpi.value for name, kpi in self._kpis.items()}

    def check_skill_promotion_trigger(self, campaign_roi: float) -> Optional[str]:
        if campaign_roi > 2.0:
            skill_id = f"campaign_roi_{hashlib.md5(str(campaign_roi).encode()).hexdigest()[:8]}"
            return skill_id
        return None


__all__ = ["BusinessKPI", "BusinessKPIDashboard"]
