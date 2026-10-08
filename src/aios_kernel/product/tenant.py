"""tenant.py - Multi-Tenant layer (E002).

Architecture:
- Tenant: top-level tenant entity (Pydantic + Envelope)
- Tier / TenantStatus: enums (free/pro/enterprise; active/suspended/deleted)
- TenantResource: abstract Pydantic that FORCES tenant_id on every
  persisted resource. This is the B003/B004 lesson from Phase B: any
  cache / memory that omits tenant_id leaks across tenants.
- TenantIsolation: stamps tenant_id onto new resources safely
- TenantRegistry: create / get / list / suspend / delete tenants
- TenantScopedRepository: per-tenant dict store; cross-tenant access
  raises CrossTenantAccessDenied and records an audit entry
- TenantAuditor: in-process log of every cross-tenant probe

The repository is intentionally NOT backed by a generic SQL store here.
The contract is: every query method takes a tenant_id and only ever
returns resources for that tenant. The downstream persistence layer
(T0032 SQLAlchemy ORM) inherits from this contract; adding real
SQL storage is out of scope for E002.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import Field, field_validator

from aios_kernel.domain.envelope import Envelope, utcnow


# ---------- Enums --------------------------------------------------------


class Tier(str, Enum):
    """Tenant pricing tier. Controls quotas in downstream modules (E003)."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


TIERS: list[str] = [t.value for t in Tier]


class TenantStatus(str, Enum):
    """Lifecycle status. DELETED is soft-delete (resources retained for audit)."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


# ---------- Exceptions --------------------------------------------------


class CrossTenantAccessDenied(Exception):
    """Raised when code attempts to access a resource under a different tenant.

    The auditor (if attached) always records a 'denied' entry before this
    is raised, so the security team has a complete trail of attempts.
    """

    def __init__(
        self,
        actor_tenant_id: str,
        resource_tenant_id: str,
        resource_id: str,
        action: str,
    ) -> None:
        self.actor_tenant_id = actor_tenant_id
        self.resource_tenant_id = resource_tenant_id
        self.resource_id = resource_id
        self.action = action
        super().__init__(
            f"Cross-tenant access denied: actor_tenant={actor_tenant_id} "
            f"resource_tenant={resource_tenant_id} resource_id={resource_id} action={action}"
        )


# ---------- Pydantic Models ---------------------------------------------


class Tenant(Envelope):
    """A single tenant in the multi-tenant system.

    Fields beyond the Envelope base:
    - name: human-readable, unique (case-insensitive) among non-deleted tenants
    - tier: pricing tier (free | pro | enterprise)
    - status: lifecycle (active | suspended | deleted)
    - metadata: free-form JSON metadata (region, plan_start, contact, ...)
    - admin_user_ids: list of user ids that have tenant-admin privileges
      (downstream E004 RBAC uses this list)
    """

    name: str = Field(..., min_length=1, max_length=200)
    tier: Tier = Tier.FREE
    status: TenantStatus = TenantStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)
    admin_user_ids: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("tenant name must be a non-empty string")
        return value.strip()

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    def is_admin(self, user_id: str) -> bool:
        return user_id in self.admin_user_ids


class TenantResource(Envelope):
    """Abstract Pydantic base for any tenant-owned resource.

    Forces every subclass to carry a non-empty UUID `tenant_id`. Subclasses
    MUST NOT override `tenant_id` -- the whole point is that isolation is
    a structural invariant, not a convention.

    The id (UUID) and created_at / updated_at come from Envelope, so every
    resource is uniquely identified by (tenant_id, id).
    """

    tenant_id: str = Field(
        ...,
        min_length=1,
        description="Owning tenant UUID (required for isolation).",
    )

    @field_validator("tenant_id")
    @classmethod
    def _validate_tenant_id(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("tenant_id is required and must not be blank")
        try:
            uuid.UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(f"tenant_id must be a valid UUID, got {value!r}") from exc
        return value


# A concrete subclass for downstream modules and for tests. The product
# layer will grow more TenantResource subclasses in E003 (BillingEvent)
# and E004 (RBACRole).
class ExampleResource(TenantResource):
    """A trivial tenant-owned resource used for tests and demos."""

    name: str = Field(..., min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------- TenantIsolation helper --------------------------------------


class TenantIsolation:
    """Stamps tenant_id onto new resources safely.

    Construct with the actor tenant, then call .stamp(resource_cls, **fields)
    to build a new resource that is guaranteed to carry the actor's
    tenant_id. Refuses to stamp if the caller passes a mismatched tenant_id
    (defence in depth against cross-tenant injection bugs).
    """

    def __init__(self, tenant: Tenant) -> None:
        if not isinstance(tenant, Tenant):
            raise TypeError(f"TenantIsolation requires a Tenant instance, got {type(tenant).__name__}")
        self._tenant_id: str = tenant.id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def stamp(self, resource_cls, **fields):
        """Create a new resource of `resource_cls` with tenant_id injected.

        Raises:
            TypeError: if resource_cls does not subclass TenantResource.
            ValueError: if the caller passed a tenant_id that does not
                match this isolation's tenant.
        """
        if not (isinstance(resource_cls, type) and issubclass(resource_cls, TenantResource)):
            raise TypeError(
                f"resource_cls must subclass TenantResource, got {resource_cls!r}"
            )
        if "tenant_id" in fields and fields["tenant_id"] != self._tenant_id:
            raise ValueError(
                f"refusing to stamp {resource_cls.__name__} with mismatched tenant_id: "
                f"isolation={self._tenant_id} field={fields['tenant_id']}"
            )
        fields["tenant_id"] = self._tenant_id
        return resource_cls(**fields)


# ---------- TenantRegistry ----------------------------------------------


class TenantRegistry:
    """In-process tenant store: create / get / list / suspend / delete."""

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}

    def create(
        self,
        name: str,
        tier: Tier = Tier.FREE,
        metadata: Optional[dict[str, Any]] = None,
        admin_user_ids: Optional[list[str]] = None,
    ) -> Tenant:
        # Reject duplicate name (case-insensitive) among non-deleted tenants.
        key = (name or "").strip().lower()
        if not key:
            raise ValueError("tenant name must be a non-empty string")
        for existing in self._tenants.values():
            if existing.status == TenantStatus.DELETED:
                continue
            if existing.name.lower() == key:
                raise ValueError(f"tenant name already exists: {name!r}")
        t = Tenant(
            name=name,
            tier=tier,
            metadata=dict(metadata or {}),
            admin_user_ids=list(admin_user_ids or []),
        )
        self._tenants[t.id] = t
        return t

    def get(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def get_or_raise(self, tenant_id: str) -> Tenant:
        t = self._tenants.get(tenant_id)
        if t is None:
            raise KeyError(f"tenant not found: {tenant_id}")
        return t

    def list(
        self,
        status: Optional[TenantStatus] = None,
        tier: Optional[Tier] = None,
    ) -> list[Tenant]:
        result = list(self._tenants.values())
        if status is not None:
            result = [t for t in result if t.status == status]
        if tier is not None:
            result = [t for t in result if t.tier == tier]
        return sorted(result, key=lambda t: t.created_at)

    def suspend(self, tenant_id: str) -> Tenant:
        t = self.get_or_raise(tenant_id)
        if t.status == TenantStatus.DELETED:
            raise ValueError(f"cannot suspend deleted tenant: {tenant_id}")
        t.status = TenantStatus.SUSPENDED
        t.touch()
        return t

    def delete(self, tenant_id: str) -> Tenant:
        t = self.get_or_raise(tenant_id)
        t.status = TenantStatus.DELETED
        t.touch()
        return t

    def is_admin(self, tenant_id: str, user_id: str) -> bool:
        t = self.get(tenant_id)
        if t is None:
            return False
        return t.is_admin(user_id)

    def count(self) -> int:
        return len(self._tenants)


# ---------- TenantScopedRepository --------------------------------------


class TenantScopedRepository:
    """Repository that only ever returns resources for one tenant.

    Every query takes a `tenant_id` and filters by it. Attempting to read
    or touch a resource owned by a different tenant raises
    `CrossTenantAccessDenied` and (if an auditor is attached) records a
    'denied' entry first.

    Storage is in-process dict-of-dicts (one bucket per tenant). This is
    the contract the downstream SQLAlchemy layer (T0032) must honour; the
    E002 acceptance test asserts the contract, not the SQL implementation.
    """

    def __init__(self, resource_cls, auditor: Optional["TenantAuditor"] = None) -> None:
        if not (isinstance(resource_cls, type) and issubclass(resource_cls, TenantResource)):
            raise TypeError(
                f"resource_cls must be a TenantResource subclass, got {resource_cls!r}"
            )
        self._resource_cls = resource_cls
        self._buckets: dict[str, dict[str, TenantResource]] = {}
        self._auditor = auditor

    @property
    def resource_cls(self):
        return self._resource_cls

    def _bucket(self, tenant_id: str) -> dict[str, TenantResource]:
        # Per-tenant bucket. Creating on first write keeps cross-tenant
        # write attempts out of the data structure.
        return self._buckets.setdefault(tenant_id, {})

    def add(self, resource: TenantResource) -> TenantResource:
        if not isinstance(resource, self._resource_cls):
            raise TypeError(
                f"repository expects {self._resource_cls.__name__}, "
                f"got {type(resource).__name__}"
            )
        self._bucket(resource.tenant_id)[resource.id] = resource
        return resource

    def get(self, tenant_id: str, resource_id: str) -> Optional[TenantResource]:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        return self._bucket(tenant_id).get(resource_id)

    def get_or_raise(self, tenant_id: str, resource_id: str) -> TenantResource:
        res = self.get(tenant_id, resource_id)
        if res is None:
            raise KeyError(
                f"{self._resource_cls.__name__} not found: "
                f"tenant={tenant_id} id={resource_id}"
            )
        return res

    def list(self, tenant_id: str) -> list[TenantResource]:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        return list(self._bucket(tenant_id).values())

    def delete(self, tenant_id: str, resource_id: str) -> bool:
        bucket = self._bucket(tenant_id)
        if resource_id in bucket:
            del bucket[resource_id]
            return True
        return False

    def count(self, tenant_id: str) -> int:
        return len(self._bucket(tenant_id))

    def total_count(self) -> int:
        """Sum across all tenants. Intended for diagnostics, not queries."""
        return sum(len(b) for b in self._buckets.values())

    # ---- Cross-tenant probes (audited) --------------------------------

    def probe_cross_tenant(
        self,
        actor_tenant_id: str,
        target_resource: TenantResource,
        action: str = "read",
    ) -> None:
        """Attempt to touch a resource owned by a different tenant.

        Always records an audit entry. Raises CrossTenantAccessDenied if
        the actor's tenant does not match the resource's tenant.
        """
        if not isinstance(target_resource, TenantResource):
            raise TypeError("target must be a TenantResource")
        if actor_tenant_id != target_resource.tenant_id:
            if self._auditor is not None:
                self._auditor.record(
                    actor_tenant_id=actor_tenant_id,
                    target_tenant_id=target_resource.tenant_id,
                    resource_id=target_resource.id,
                    action=action,
                    verdict="denied",
                )
            raise CrossTenantAccessDenied(
                actor_tenant_id=actor_tenant_id,
                resource_tenant_id=target_resource.tenant_id,
                resource_id=target_resource.id,
                action=action,
            )
        # Same-tenant access: allowed. Record only if auditor is attached
        # (auditor is the source of truth; allow log is informational).
        if self._auditor is not None:
            self._auditor.record(
                actor_tenant_id=actor_tenant_id,
                target_tenant_id=target_resource.tenant_id,
                resource_id=target_resource.id,
                action=action,
                verdict="allowed",
            )


# ---------- TenantAuditor -----------------------------------------------


class TenantAuditor:
    """In-process audit log for cross-tenant access attempts.

    The log is append-only from the outside; clear() exists for tests.
    Entries are dicts with: ts, actor_tenant_id, target_tenant_id,
    resource_id, action, verdict (allowed | denied).
    """

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def record(
        self,
        *,
        actor_tenant_id: str,
        target_tenant_id: str,
        resource_id: str,
        action: str,
        verdict: str,
    ) -> dict[str, Any]:
        if verdict not in ("allowed", "denied"):
            raise ValueError(f"verdict must be 'allowed' or 'denied', got {verdict!r}")
        entry = {
            "ts": utcnow().isoformat(),
            "actor_tenant_id": actor_tenant_id,
            "target_tenant_id": target_tenant_id,
            "resource_id": resource_id,
            "action": action,
            "verdict": verdict,
        }
        self.entries.append(entry)
        return entry

    def denied_attempts(self) -> list[dict[str, Any]]:
        return [e for e in self.entries if e["verdict"] == "denied"]

    def allowed_attempts(self) -> list[dict[str, Any]]:
        return [e for e in self.entries if e["verdict"] == "allowed"]

    def attempts_against_tenant(self, target_tenant_id: str) -> list[dict[str, Any]]:
        return [e for e in self.entries if e["target_tenant_id"] == target_tenant_id]

    def count(self) -> int:
        return len(self.entries)

    def clear(self) -> None:
        self.entries.clear()


__all__ = [
    "TIERS",
    "CrossTenantAccessDenied",
    "ExampleResource",
    "Tenant",
    "TenantAuditor",
    "TenantIsolation",
    "TenantRegistry",
    "TenantResource",
    "TenantScopedRepository",
    "TenantStatus",
    "Tier",
    "utcnow",
]
