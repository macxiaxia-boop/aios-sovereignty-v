"""test_crm_feedback.py - D004 CRM feedback integration tests."""
from __future__ import annotations

from aios_kernel.business.crm_feedback import (
    CATEGORY_EVENT_TYPES,
    CRMAuditor,
    CRMEvent,
    CRMIngestor,
    EventType,
    Severity,
    categorize,
    category_counts,
    hash_customer_id,
)


def test_ingest_single():
    """Smoke: ingest a single well-formed event dict -> CRMEvent."""
    ing = CRMIngestor()
    ev = ing.ingest_event({
        "customer_id": "cust_alice_001",
        "event_type": "purchase",
        "product": "plan_pro",
        "severity": "high",
        "action_recommended": True,
    })
    assert isinstance(ev, CRMEvent)
    assert ev.event_type == EventType.PURCHASE
    assert ev.severity == Severity.HIGH
    assert ev.product == "plan_pro"
    assert ev.action_recommended is True
    assert len(ev.customer_id_hash) == 16
    assert ev.ingested_at is not None


def test_hash_customer_id():
    """Hash determinism + collision-resistance for customer_id (PII)."""
    h1 = hash_customer_id("cust_alice_001")
    h2 = hash_customer_id("cust_alice_001")
    h3 = hash_customer_id("cust_bob_002")
    # Deterministic
    assert h1 == h2
    # 16 hex chars
    assert len(h1) == 16
    all(c in "0123456789abcdef" for c in h1)
    # Different input -> different hash
    assert h1 != h3
    # Raw customer_id must NOT appear in the hash or in the event record
    ing = CRMIngestor()
    ev = ing.ingest_event({"customer_id": "secret_alice_xyz", "event_type": "feedback"})
    assert "secret_alice_xyz" not in ev.customer_id_hash
    assert "secret_alice_xyz" not in ev.model_dump_json()


def test_categorize_correct():
    """categorize returns all 5 canonical buckets; counts sum to total."""
    ing = CRMIngestor()
    rows = [
        {"customer_id": f"c{i}", "event_type": t}
        for i, t in enumerate(
            ["churn", "upsell", "support", "feedback", "purchase"]
            * 20  # 100 events, 20 each
        )
    ]
    events = ing.ingest_bulk(rows)
    buckets = categorize(events)
    counts = category_counts(buckets)
    assert set(buckets.keys()) == {"churn", "upsell", "feedback", "support", "purchase"}
    assert all(v == 20 for v in counts.values())
    assert sum(counts.values()) == 100
    # Each bucket is a list of CRMEvent
    for evs in buckets.values():
        assert all(isinstance(e, CRMEvent) for e in evs)


def test_privacy_already_500():
    """PII boundary test: 500 events -> zero raw customer_id leaks."""
    ing = CRMIngestor()
    rows = [
        {"customer_id": f"secret_cust_{i:04d}", "event_type": "feedback"}
        for i in range(500)
    ]
    events = ing.ingest_bulk(rows)
    assert len(events) == 500
    # Each event: customer_id_hash exists, raw never persisted
    seen_hashes = set()
    for ev in events:
        assert len(ev.customer_id_hash) == 16
        seen_hashes.add(ev.customer_id_hash)
    # 500 unique hashes for 500 unique customer_ids
    assert len(seen_hashes) == 500
    # Dump every event; raw customer_id must NEVER appear
    for i, ev in enumerate(events):
        raw = f"secret_cust_{i:04d}"
        dump = ev.model_dump_json()
        assert raw not in dump, f"PII leak on event {i}: {raw}"
    # Bulk ingest 1000 events (D004 evidence requirement)
    big = [
        {"customer_id": f"big_cust_{i}", "event_type": ["churn","upsell","support","feedback","purchase"][i % 5]}
        for i in range(1000)
    ]
    big_events = ing.ingest_bulk(big)
    assert len(big_events) == 1000


def test_audit():
    """Audit log captures every ingested event (PII-safe entries)."""
    auditor = CRMAuditor()
    ing = CRMIngestor(auditor=auditor)
    rows = [
        {"customer_id": f"audit_cust_{i}", "event_type": "purchase", "action_recommended": (i % 2 == 0)}
        for i in range(25)
    ]
    events = ing.ingest_bulk(rows)
    assert len(events) == 25
    log = auditor.log
    assert len(log) == 25
    for entry, ev in zip(log, events):
        assert entry["event_id"] == ev.id
        assert entry["customer_id_hash"] == ev.customer_id_hash
        assert entry["event_type"] == "purchase"
        assert "recorded_at" in entry
        assert "audit_cust_" not in entry["customer_id_hash"]
    # CATEGORY_EVENT_TYPES has all 5 buckets with non-empty keyword lists
    assert set(CATEGORY_EVENT_TYPES.keys()) == {"churn","upsell","support","feedback","purchase"}
    for kws in CATEGORY_EVENT_TYPES.values():
        assert len(kws) > 0
