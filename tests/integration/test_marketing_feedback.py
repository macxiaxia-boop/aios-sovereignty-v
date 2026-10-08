"""test_marketing_feedback.py — D005 Marketing Feedback + Skill recommendation.

5 integration test cases (D005 §Scope):
  1. test_track_basic
       A campaign is appended to the service; ``get_campaigns()`` reflects it;
       the returned object is the same instance the service stored.

  2. test_roi_calc
       ROI = (conversions * value_per_conversion - cost) / cost when cost > 0.
       ROI is undefined (None) when cost == 0.
       The model validator keeps ROI consistent with the source numbers
       even after construction (Envelope.validate_assignment).

  3. test_skill_recommendation
       A campaign with ROI strictly above the default threshold (2.0)
       produces a SkillRecommendation whose skill_id, channel, roi,
       and audit_log are populated. Idempotency: a second call returns
       the SAME recommendation rather than duplicating.

  4. test_low_roi_skip
       A campaign with ROI <= threshold produces NO recommendation
       (returns None). A campaign with cost == 0 (ROI undefined) also
       returns None.

  5. test_audit_and_100_campaigns
       100 campaigns tracked; count_campaigns() == 100. Every
       SkillRecommendation has a non-empty audit_log with the ROI and
       threshold line. The service logs (info) on every track_campaign.

Run:  pytest tests/integration/test_marketing_feedback.py -v
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# 1. track_basic
# ---------------------------------------------------------------------------


def test_track_basic_appends_and_returns_same_instance():
    """A campaign is appended; the service stores it and returns the
    same instance (no defensive copy)."""
    from aios_kernel.business import (
        Channel,
        MarketingCampaign,
        MarketingFeedbackService,
    )

    svc = MarketingFeedbackService()
    camp = MarketingCampaign(
        name="spring-promo",
        channel=Channel.EMAIL,
        impressions=5000,
        conversions=25,
        cost=200.0,
    )
    returned = svc.track_campaign(camp)

    assert returned is camp, "service must return the same instance"
    assert svc.count_campaigns() == 1
    stored = svc.get_campaigns()
    assert len(stored) == 1
    assert stored[0].name == "spring-promo"
    assert stored[0].channel == Channel.EMAIL
    assert stored[0].impressions == 5000
    assert stored[0].conversions == 25
    assert stored[0].cost == 200.0


# ---------------------------------------------------------------------------
# 2. roi_calc
# ---------------------------------------------------------------------------


def test_roi_calc_correct_formula_and_zero_cost_undefined():
    """ROI = (conversions * value_per_conversion - cost) / cost.

    Cost == 0 → roi is None (undefined; we do not fake a metric).
    """
    from aios_kernel.business import (
        Channel,
        MarketingCampaign,
        DEFAULT_VALUE_PER_CONVERSION,
    )

    # 1) Standard case: 50 conv * ¥100 - 20 cost  ->  ROI = (5000-20)/20 = 249.0
    camp = MarketingCampaign(
        name="high-roll",
        channel=Channel.SOCIAL,
        impressions=10_000,
        conversions=50,
        cost=20.0,
    )
    expected = (50 * DEFAULT_VALUE_PER_CONVERSION - 20.0) / 20.0
    assert camp.roi == pytest.approx(expected)
    assert camp.revenue == pytest.approx(50 * DEFAULT_VALUE_PER_CONVERSION)
    assert camp.profit == pytest.approx(50 * DEFAULT_VALUE_PER_CONVERSION - 20.0)

    # 2) Custom value_per_conversion
    camp2 = MarketingCampaign(
        name="premium",
        channel=Channel.SEARCH,
        impressions=10_000,
        conversions=10,
        cost=200.0,
        value_per_conversion=500.0,
    )
    expected2 = (10 * 500.0 - 200.0) / 200.0  # 24.0
    assert camp2.roi == pytest.approx(expected2)

    # 3) Negative ROI (revenue < cost): 1 conv * ¥100 - 200 cost  ->  ROI = -0.5
    camp3 = MarketingCampaign(
        name="loss-leader",
        channel=Channel.DISPLAY,
        impressions=10_000,
        conversions=1,
        cost=200.0,
    )
    assert camp3.roi == pytest.approx(-0.5)  # (100 - 200) / 200

    # 4) Zero cost → undefined
    camp4 = MarketingCampaign(
        name="freebie",
        channel=Channel.CONTENT,
        impressions=10_000,
        conversions=10,
        cost=0.0,
    )
    assert camp4.roi is None, "ROI must be None when cost == 0"
    assert camp4.is_high_roi() is False


def test_roi_validator_consistent_across_field_set():
    """When a caller mutates a field on a constructed instance, the model
    validator (Envelope.validate_assignment=True) must keep ROI in
    lock-step with conversions/cost/value_per_conversion."""
    from aios_kernel.business import Channel, MarketingCampaign

    camp = MarketingCampaign(
        name="recompute",
        channel=Channel.EMAIL,
        impressions=1000,
        conversions=10,
        cost=200.0,
    )
    initial_roi = camp.roi
    assert initial_roi == pytest.approx(4.0)

    # Push conversions way up; ROI must follow on the assignment.
    camp.conversions = 100
    # (100 * 100 - 200) / 200 = 49.0
    assert camp.roi == pytest.approx(49.0)

    # And cost up; ROI must fall.
    camp.cost = 9800.0
    # (100 * 100 - 9800) / 9800 = (10000 - 9800) / 9800 ≈ 0.020408
    expected_after = (100 * 100 - 9800.0) / 9800.0
    assert camp.roi == pytest.approx(expected_after)

    # Zero cost on assignment → ROI undefined.
    camp.cost = 0.0
    assert camp.roi is None


# ---------------------------------------------------------------------------
# 3. skill_recommendation
# ---------------------------------------------------------------------------


def test_skill_recommendation_high_roi_emits_recommendation():
    """ROI > threshold → SkillRecommendation emitted; skill_id, channel,
    roi, reason, audit_log all populated; idempotent on repeated calls."""
    from aios_kernel.business import (
        Channel,
        DEFAULT_ROI_THRESHOLD,
        MarketingCampaign,
        MarketingFeedbackService,
    )

    svc = MarketingFeedbackService()
    camp = MarketingCampaign(
        name="winner",
        channel=Channel.EMAIL,
        impressions=10_000,
        conversions=50,
        cost=200.0,
    )
    # Sanity: this campaign IS high-ROI (>2.0 default threshold).
    assert camp.roi is not None
    assert camp.roi > DEFAULT_ROI_THRESHOLD

    rec1 = svc.recommend_skill_promotion(camp)
    assert rec1 is not None
    assert rec1.campaign_id == camp.id
    assert rec1.campaign_name == "winner"
    assert rec1.channel == Channel.EMAIL
    assert rec1.roi == camp.roi
    assert rec1.skill_id.startswith("skill_email_"), (
        f"auto-generated skill_id must include channel; got {rec1.skill_id!r}"
    )
    assert "exceeds threshold" in rec1.reason
    assert isinstance(rec1.audit_log, list) and len(rec1.audit_log) >= 4
    assert any("roi=" in line for line in rec1.audit_log)
    assert any("threshold=" in line for line in rec1.audit_log)
    # Audit timestamps must be tz-aware UTC.
    ts_line = next(l for l in rec1.audit_log if l.startswith("recommended_at="))
    ts_iso = ts_line.split("=", 1)[1]
    parsed = datetime.fromisoformat(ts_iso)
    assert parsed.tzinfo is not None

    # Idempotency: a second call returns the SAME instance, does not
    # create a duplicate.
    rec2 = svc.recommend_skill_promotion(camp)
    assert rec2 is rec1
    assert svc.count_recommendations() == 1

    # Custom skill_id is respected verbatim.
    camp_explicit = MarketingCampaign(
        name="explicit-skill",
        channel=Channel.SOCIAL,
        conversions=80,
        cost=200.0,
        skill_id="my_custom_skill_42",
    )
    rec3 = svc.recommend_skill_promotion(camp_explicit)
    assert rec3 is not None
    assert rec3.skill_id == "my_custom_skill_42"
    assert svc.count_recommendations() == 2


# ---------------------------------------------------------------------------
# 4. low_roi_skip
# ---------------------------------------------------------------------------


def test_low_roi_skip_returns_none():
    """ROI <= threshold → no promotion. Cost == 0 → no promotion."""
    from aios_kernel.business import (
        Channel,
        MarketingCampaign,
        MarketingFeedbackService,
    )

    svc = MarketingFeedbackService()

    # Boundary case: ROI well below threshold → not promoted.
    boundary_camp = MarketingCampaign(
        name="boundary",
        channel=Channel.SEARCH,
        impressions=10_000,
        conversions=20,
        cost=1000.0,
    )
    # 20 conv * 100 - 1000 cost  = 1000; 1000/1000 = 1.0 (below 2.0 threshold)
    assert boundary_camp.roi == pytest.approx(1.0)
    assert svc.recommend_skill_promotion(boundary_camp) is None

    # Strictly above threshold → still not promoted at raised threshold.
    high_camp = MarketingCampaign(
        name="high-but-not-higher",
        channel=Channel.DISPLAY,
        conversions=30,
        cost=1000.0,
    )
    # 30*100 - 1000 = 2000; 2000/1000 = 2.0  == threshold → not promoted.
    assert svc.recommend_skill_promotion(high_camp, threshold=2.0) is None
    # But promoted when threshold is lowered to 1.5.
    rec = svc.recommend_skill_promotion(high_camp, threshold=1.5)
    assert rec is not None

    # Negative ROI → not promoted.
    loss_camp = MarketingCampaign(
        name="loss",
        channel=Channel.EMAIL,
        conversions=1,
        cost=500.0,
    )
    assert loss_camp.roi is not None and loss_camp.roi < 0
    assert svc.recommend_skill_promotion(loss_camp) is None

    # Zero cost → ROI undefined → not promoted.
    free_camp = MarketingCampaign(
        name="free",
        channel=Channel.CONTENT,
        conversions=10,
        cost=0.0,
    )
    assert free_camp.roi is None
    assert svc.recommend_skill_promotion(free_camp) is None

    # count_recommendations reflects ONLY the one explicit promotion above.
    assert svc.count_recommendations() == 1


# ---------------------------------------------------------------------------
# 5. audit + 100 campaigns
# ---------------------------------------------------------------------------


def test_audit_and_100_campaigns(caplog):
    """100 campaigns tracked; every track() emits an info log; every
    SkillRecommendation has a non-empty audit_log with ROI + threshold
    entries."""
    from aios_kernel.business import (
        Channel,
        MarketingCampaign,
        MarketingFeedbackService,
    )

    svc = MarketingFeedbackService()
    expected_recs = 0

    with caplog.at_level(logging.INFO, logger="aios_kernel.business.marketing_feedback"):
        # 70 normal (mixed ROI), 30 zero-cost.
        for i in range(70):
            conversions = i + 1
            # Vary cost so we get a mix of high / mid / low ROI.
            if i % 3 == 0:
                cost = 100.0
                roi = conversions - 1
            elif i % 3 == 1:
                cost = 1000.0
                roi = (conversions * 100 - 1000) / 1000
            else:
                cost = 5000.0
                roi = (conversions * 100 - 5000) / 5000
            camp = MarketingCampaign(
                name=f"campaign-{i:03d}",
                channel=Channel(list(Channel)[i % 5]),
                impressions=1000 * (i + 1),
                conversions=conversions,
                cost=cost,
            )
            assert camp.roi == pytest.approx(roi)
            svc.track_campaign(camp)
            rec = svc.recommend_skill_promotion(camp)
            if rec is not None:
                expected_recs += 1
                assert rec.audit_log, "audit_log must be non-empty"
                joined = "\n".join(rec.audit_log)
                assert "roi=" in joined
                assert "threshold=" in joined
                assert "channel=" in joined

        for i in range(70, 100):
            camp = MarketingCampaign(
                name=f"free-{i:03d}",
                channel=Channel.CONTENT,
                impressions=10_000,
                conversions=10,
                cost=0.0,
            )
            svc.track_campaign(camp)
            # zero-cost → never promoted
            assert svc.recommend_skill_promotion(camp) is None

    assert svc.count_campaigns() == 100, (
        f"expected 100 tracked campaigns, got {svc.count_campaigns()}"
    )

    # Every track_campaign emits an info log line.
    track_lines = [
        rec for rec in caplog.records
        if rec.name == "aios_kernel.business.marketing_feedback"
        and "track_campaign" in rec.getMessage()
    ]
    assert len(track_lines) == 100, (
        f"expected 100 track_campaign log lines, got {len(track_lines)}"
    )

    # Count recommendations matches the expected count.
    assert svc.count_recommendations() == expected_recs, (
        f"expected {expected_recs} recommendations, got {svc.count_recommendations()}"
    )

    # All recommendations have a tz-aware timestamp in their audit log.
    for rec in svc.get_recommendations():
        ts_line = next(
            (l for l in rec.audit_log if l.startswith("recommended_at=")), None
        )
        assert ts_line is not None
        ts = datetime.fromisoformat(ts_line.split("=", 1)[1])
        assert ts.tzinfo is not None
        # Must be within the last 5 minutes (we just generated them).
        assert (datetime.now(UTC) - ts) < timedelta(minutes=5)