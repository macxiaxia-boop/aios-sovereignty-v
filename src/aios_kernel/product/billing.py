"""billing.py - E003 Billing & Credits tracking."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Literal, Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow


class BillingEvent(Envelope):
    tenant_id: str
    event_type: Literal["api_call", "storage", "compute", "skill_use"] = "api_call"
    quantity: float = 1.0
    cost_usd: float = 0.0
    credits_used: float = 0.0
    stripe_charge_id: Optional[str] = None


class BillingTracker:
    PRICING = {"api_call": 0.001, "storage": 0.01, "compute": 0.05, "skill_use": 0.10}

    def __init__(self):
        self._events: list[BillingEvent] = []
        self._credits: dict[str, float] = {}

    def add_credits(self, tenant_id: str, credits: float) -> None:
        self._credits[tenant_id] = self._credits.get(tenant_id, 0.0) + credits

    def get_credits(self, tenant_id: str) -> float:
        return self._credits.get(tenant_id, 0.0)

    def track_event(self, tenant_id: str, event_type: str, quantity: float = 1.0) -> BillingEvent:
        cost = self.PRICING.get(event_type, 0.001) * quantity
        credits_available = self._credits.get(tenant_id, 0.0)
        credits_used = min(cost, credits_available) if credits_available > 0 else 0.0
        ev = BillingEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            quantity=quantity,
            cost_usd=cost,
            credits_used=credits_used,
            stripe_charge_id=f"ch_mock_{uuid.uuid4().hex[:8]}",
        )
        self._events.append(ev)
        if credits_used > 0:
            self._credits[tenant_id] -= credits_used
        return ev

    def get_events(self, tenant_id: str) -> list:
        return [e for e in self._events if e.tenant_id == tenant_id]


__all__ = ["BillingEvent", "BillingTracker"]
