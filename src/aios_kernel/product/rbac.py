"""rbac.py - E004 Enterprise Permission (RBAC)."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow


class RBACRole(Envelope):
    name: str
    permissions: list[str] = Field(default_factory=list)
    tenant_id: Optional[str] = None

    def has_permission(self, resource: str, action: str) -> bool:
        return f"{resource}:{action}" in self.permissions or "*:*" in self.permissions


class RBACManager:
    def __init__(self):
        self._roles: dict[str, RBACRole] = {}
        self._audit_log: list[dict] = []

    def create_role(self, name: str, permissions: list[str], tenant_id: Optional[str] = None) -> RBACRole:
        r = RBACRole(name=name, permissions=permissions, tenant_id=tenant_id)
        self._roles[str(r.id)] = r
        return r

    def check(self, role_id: str, resource: str, action: str) -> bool:
        role = self._roles.get(role_id)
        allowed = role.has_permission(resource, action) if role else False
        self._audit_log.append({
            "role_id": role_id,
            "resource": resource,
            "action": action,
            "allowed": allowed,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        return allowed

    def get_audit_log(self) -> list:
        return self._audit_log


__all__ = ["RBACRole", "RBACManager"]
