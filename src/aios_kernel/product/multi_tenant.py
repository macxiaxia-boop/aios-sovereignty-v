"""multi_tenant.py - E002 Multi-Tenant layer."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Literal, Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow


class Tenant(Envelope):
    name: str
    tier: Literal["free", "pro", "enterprise"] = "free"
    metadata: dict = Field(default_factory=dict)


class TenantIsolation(Envelope):
    tenant_id: str
    resource_id: str
    resource_type: str
    access_granted: bool = True


class TenantRegistry:
    def __init__(self):
        self._tenants: dict[str, Tenant] = {}
        self._isolation_log: list[TenantIsolation] = []

    def create_tenant(self, name: str, tier: str = "free") -> Tenant:
        t = Tenant(name=name, tier=tier)
        self._tenants[str(t.id)] = t
        return t

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def check_isolation(self, tenant_id: str, resource_id: str, resource_type: str) -> TenantIsolation:
        iso = TenantIsolation(
            tenant_id=tenant_id,
            resource_id=resource_id,
            resource_type=resource_type,
            access_granted=True,
        )
        self._isolation_log.append(iso)
        return iso

    def get_isolation_log(self, tenant_id: str) -> list:
        return [i for i in self._isolation_log if i.tenant_id == tenant_id]


__all__ = ["Tenant", "TenantIsolation", "TenantRegistry"]
