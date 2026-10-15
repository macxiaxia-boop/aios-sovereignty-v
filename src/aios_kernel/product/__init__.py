"""__init__.py - aios_kernel.product (Phase E)."""
from aios_kernel.product.billing import BillingEvent, BillingTracker
from aios_kernel.product.marketplace import MarketplaceListing, MarketplaceService
from aios_kernel.product.rbac import RBACManager, RBACRole
from aios_kernel.product.tenant import (
    CrossTenantAccessDenied,
    ExampleResource,
    Tenant,
    TenantAuditor,
    TenantIsolation,
    TenantRegistry,
    TenantResource,
    TenantScopedRepository,
    TenantStatus,
    Tier,
)

__all__ = [
    "Tenant", "TenantIsolation", "TenantRegistry",
    "BillingEvent", "BillingTracker",
    "RBACRole", "RBACManager",
    "MarketplaceListing", "MarketplaceService",
]
