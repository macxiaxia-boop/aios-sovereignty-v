"""marketplace.py - E005 Workflow Marketplace."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow


class MarketplaceListing(Envelope):
    skill_id: str
    seller_tenant_id: str
    price_usd: float = 0.0
    sales_count: int = 0
    rating: float = 0.0


class MarketplaceService:
    def __init__(self):
        self._listings: dict[str, MarketplaceListing] = {}
        self._purchases: list[dict] = []

    def list_skill(self, skill_id: str, seller_tenant_id: str, price_usd: float = 9.99) -> MarketplaceListing:
        listing = MarketplaceListing(
            skill_id=skill_id,
            seller_tenant_id=seller_tenant_id,
            price_usd=price_usd,
            sales_count=0,
            rating=0.0,
        )
        self._listings[str(listing.id)] = listing
        return listing

    def purchase_skill(self, buyer_tenant_id: str, listing_id: str) -> dict:
        listing = self._listings.get(listing_id)
        if not listing:
            raise ValueError("listing not found")
        seller_share = listing.price_usd * 0.7
        platform_share = listing.price_usd * 0.3
        listing.sales_count += 1
        receipt = {
            "buyer": buyer_tenant_id,
            "seller": listing.seller_tenant_id,
            "price_usd": listing.price_usd,
            "seller_share": seller_share,
            "platform_share": platform_share,
            "skill_id": listing.skill_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._purchases.append(receipt)
        return receipt

    def get_listings(self) -> list:
        return list(self._listings.values())

    def get_purchases(self, tenant_id: str) -> list:
        return [p for p in self._purchases if p["buyer"] == tenant_id]


__all__ = ["MarketplaceListing", "MarketplaceService"]
