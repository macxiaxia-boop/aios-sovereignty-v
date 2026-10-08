"""__init__.py - aios_kernel.product (Phase E)."""
from aios_kernel.product.multi_tenant import Tenant, TenantIsolation, TenantRegistry
from aios_kernel.product.billing import BillingEvent, BillingTracker
from aios_kernel.product.rbac import RBACRole, RBACManager
from aios_kernel.product.marketplace import MarketplaceListing, MarketplaceService

__all__ = [
    "Tenant", "TenantIsolation", "TenantRegistry",
    "BillingEvent", "BillingTracker",
    "RBACRole", "RBACManager",
    "MarketplaceListing", "MarketplaceService",
]
