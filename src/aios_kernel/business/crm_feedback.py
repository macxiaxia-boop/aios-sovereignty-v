"""crm_feedback.py - D004 CRM Feedback ingestion.

PII-safe ingestion:
- raw customer_id NEVER persisted; only SHA-256[:16] hash
- ingest_event takes a dict and returns a CRMEvent with hashed customer_id_hash

Categorization (5 categories, by event_type prefix):
- churn     : risk signals (cancel/refund/uninstall/unsubscribe)
- upsell    : upgrade / expansion / add-on signals
- support   : ticket / help / complaint / inquiry
- feedback  : review / rating / survey / nps
- purchase  : buy / order / checkout / renewal
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow


# ---------- Enums -------------------------------------------------------

class EventType(str, Enum):
    """5 CRM event types (per D004 scope)."""
    CHURN = "churn"
    UPSELL = "upsell"
    SUPPORT = "support"
    FEEDBACK = "feedback"
    PURCHASE = "purchase"


class Severity(str, Enum):
    """Severity of a CRM event (used for routing/prioritization)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


CATEGORY_EVENT_TYPES: dict[str, list[str]] = {
    # category -> list of normalized event keywords that map into it
    "churn": [
        "cancel", "cancellation", "churn", "refund",
        "uninstall", "unsubscribe", "downgrade",
    ],
    "upsell": [
        "upgrade", "upsell", "expand", "expansion",
        "add_on", "addon", "tier_up", "seat_added",
    ],
    "support": [
        "ticket", "support", "complaint", "inquiry",
        "help_request", "issue", "bug_report",
    ],
    "feedback": [
        "review", "rating", "feedback", "survey", "nps",
        "testimonial", "comment",
    ],
    "purchase": [
        "buy", "purchase", "order", "checkout",
        "renewal", "renew", "signup", "paid",
    ],
}


# ---------- Pydantic Model ----------------------------------------------

class CRMEvent(Envelope):
    """A single CRM feedback event (PII-sanitized).

    `customer_id_hash` holds a SHA-256[:16] of the raw customer_id.
    The raw customer_id MUST NEVER be persisted on this object.
    """
    customer_id_hash: str = Field(
        ...,
        min_length=16,
        max_length=16,
        description="SHA-256[:16] of raw customer_id (PII-safe).",
    )
    event_type: EventType
    severity: Severity = Severity.MEDIUM
    product: str = ""
    action_recommended: bool = False
    ingested_at: Optional[datetime] = None


# ---------- Helpers -----------------------------------------------------

def hash_customer_id(raw_customer_id: str) -> str:
    """Return SHA-256[:16] of the raw customer_id (16 hex chars)."""
    if not isinstance(raw_customer_id, str) or not raw_customer_id:
        raise ValueError("customer_id must be a non-empty string")
    return hashlib.sha256(raw_customer_id.encode("utf-8")).hexdigest()[:16]


# ---------- Ingestion ---------------------------------------------------

class CRMAuditor:
    """In-memory audit log (PII-safe entries only)."""

    def __init__(self) -> None:
        self._log: list[dict[str, Any]] = []

    def record(self, event: CRMEvent, *, source: str = "ingest") -> None:
        self._log.append({
            "event_id": event.id,
            "customer_id_hash": event.customer_id_hash,
            "event_type": event.event_type.value,
            "action_recommended": event.action_recommended,
            "source": source,
            "recorded_at": utcnow().isoformat(),
        })

    @property
    def log(self) -> list[dict[str, Any]]:
        return list(self._log)

    def __len__(self) -> int:
        return len(self._log)


class CRMIngestor:
    """Ingest raw CRM event dicts into PII-sanitized CRMEvent records."""

    REQUIRED_FIELDS = ("customer_id", "event_type")

    def __init__(self, auditor: Optional[CRMAuditor] = None) -> None:
        self._events: list[CRMEvent] = []
        self._auditor = auditor if auditor is not None else CRMAuditor()

    @property
    def events(self) -> list[CRMEvent]:
        return list(self._events)

    @property
    def auditor(self) -> CRMAuditor:
        return self._auditor

    def ingest_event(self, event_dict: dict[str, Any]) -> CRMEvent:
        """Ingest a single raw event dict.

        - Hashes customer_id (PII)
        - Defaults severity=medium, action_recommended=False
        - Auto-audits the resulting event
        """
        if not isinstance(event_dict, dict):
            raise TypeError("event_dict must be a dict")

        missing = [f for f in self.REQUIRED_FIELDS if f not in event_dict or event_dict[f] in (None, "")]
        if missing:
            raise ValueError(f"missing required field(s): {missing}")

        raw_event_type = str(event_dict["event_type"]).lower().strip()
        try:
            event_type = EventType(raw_event_type)
        except ValueError:
            # Allow free-form keywords by mapping via CATEGORY_EVENT_TYPES
            mapped_category = _keyword_to_category(raw_event_type)
            if mapped_category is None:
                raise ValueError(f"unknown event_type: {event_dict['event_type']!r}")
            event_type = EventType(mapped_category)

        severity_raw = event_dict.get("severity", "medium")
        try:
            severity = Severity(str(severity_raw).lower().strip())
        except ValueError:
            severity = Severity.MEDIUM

        product = str(event_dict.get("product", "") or "")
        action_recommended = bool(event_dict.get("action_recommended", False))

        ev = CRMEvent(
            id=str(uuid.uuid4()),
            customer_id_hash=hash_customer_id(str(event_dict["customer_id"])),
            event_type=event_type,
            severity=severity,
            product=product,
            action_recommended=action_recommended,
            ingested_at=utcnow(),
        )
        self._events.append(ev)
        self._auditor.record(ev, source="ingest")
        return ev

    def ingest_bulk(self, events: list[dict[str, Any]]) -> list[CRMEvent]:
        """Ingest many events in one call."""
        return [self.ingest_event(e) for e in events]


# ---------- Categorization ----------------------------------------------

def _keyword_to_category(keyword: str) -> Optional[str]:
    """Map a free-form keyword to one of the 5 categories (case-insensitive)."""
    k = keyword.lower().strip()
    for category, keywords in CATEGORY_EVENT_TYPES.items():
        if k in keywords:
            return category
    return None


def categorize(events: list[CRMEvent]) -> dict[str, list[CRMEvent]]:
    """Group events into the 5 canonical categories.

    Returns: dict with keys churn/upsell/support/feedback/purchase.
    All 5 keys are always present; empty lists when no events for a category.
    """
    buckets: dict[str, list[CRMEvent]] = {
        "churn": [],
        "upsell": [],
        "support": [],
        "feedback": [],
        "purchase": [],
    }
    for ev in events:
        category = ev.event_type.value
        if category not in buckets:
            # Unknown event_type -> drop into 'feedback' as the safe default
            category = "feedback"
        buckets[category].append(ev)
    return buckets


def category_counts(buckets: dict[str, list[CRMEvent]]) -> dict[str, int]:
    """Return count of events per category (all 5 keys, sum == len(events))."""
    return {k: len(v) for k, v in buckets.items()}


__all__ = [
    "EventType",
    "Severity",
    "CATEGORY_EVENT_TYPES",
    "CRMEvent",
    "CRMAuditor",
    "CRMIngestor",
    "hash_customer_id",
    "categorize",
    "category_counts",
]
