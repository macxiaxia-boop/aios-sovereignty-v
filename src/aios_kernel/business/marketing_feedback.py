"""marketing_feedback.py — D005 Marketing Feedback + Skill recommendation.

Phase D (Track 6, VNext Phase D — Business). Owns:

  - ``MarketingCampaign`` — Pydantic v2 schema for one campaign.
        Fields: id (Envelope), name, channel, impressions, conversions,
        cost, value_per_conversion, skill_id (optional), and the
        computed ``roi`` field.

        ROI is derived deterministically from the campaign's own data:

            revenue      = conversions * value_per_conversion
            roi          = (revenue - cost) / cost      if cost > 0
            roi          = None                          if cost == 0

        The model raises on non-finite inputs and refuses to lie about
        ROI when cost is zero — that is the contract.

  - ``SkillRecommendation`` — a record emitted when a high-ROI campaign
        is materialised as a reusable skill. Carries the campaign's ROI,
        audit_log, and the skill_id it would be promoted under.

  - ``MarketingFeedbackService`` — process-level service with two
        public verbs:

            track_campaign(campaign)
                Append the campaign (with computed ROI) to the service
                log and emit a non-silent kernel log line so the
                operator can grep for tracking events.

            recommend_skill_promotion(campaign, *, threshold=2.0)
                If the campaign's ROI is strictly greater than the
                threshold, emit a SkillRecommendation (idempotent: a
                second call for the same campaign returns the existing
                recommendation rather than a duplicate).

        The default threshold (2.0) is the card's spec — high-ROI
        campaigns earn promotion to a reusable skill.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any, ClassVar

from pydantic import Field, field_validator, model_validator

from aios_kernel.domain.envelope import Envelope, utcnow

logger = logging.getLogger("aios_kernel.business.marketing_feedback")


# ---------------------------------------------------------------------------
# Enums / constants
# ---------------------------------------------------------------------------


class Channel(str, Enum):
    """5 canonical marketing channels (D005 Scope)."""

    EMAIL = "email"
    SOCIAL = "social"
    SEARCH = "search"
    DISPLAY = "display"
    CONTENT = "content"


# Default monetary value per conversion, in CNY (¥). Tunable per
# campaign via ``MarketingCampaign.value_per_conversion``.
DEFAULT_VALUE_PER_CONVERSION = 100.0

# Default ROI threshold above which a campaign earns a SkillRecommendation.
# Card spec: "ROI > 2.0 → 物化为 skill".
DEFAULT_ROI_THRESHOLD = 2.0


def _compute_roi(conversions: int, cost: float, value_per_conversion: float) -> float | None:
    """Pure helper — ROI = (conversions * value - cost) / cost when cost > 0.

    Cost == 0 → None (undefined; do NOT fake a number — Forbidden:
    "假 metrics (无 ROI 计算)").
    """
    if cost > 0:
        return (float(conversions) * float(value_per_conversion) - float(cost)) / float(cost)
    return None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class MarketingCampaign(Envelope):
    """A marketing campaign with auto-computed ROI.

    Inherits ``id`` / ``created_at`` / ``updated_at`` / ``schema_version``
    from :class:`aios_kernel.domain.envelope.Envelope`.

    ROI is computed deterministically from the campaign's own data:

        - on construction (model_validator(mode="before") injects the
          value into the dict before the model is built),
        - and on every subsequent field assignment (model_validator(
          mode="after") recomputes and writes back via
          ``object.__setattr__`` to bypass ``validate_assignment`` and
          avoid recursion).
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    name: str = Field(..., min_length=1, max_length=200, description="Campaign name.")
    channel: Channel = Field(..., description="Marketing channel.")
    impressions: int = Field(default=0, ge=0, description="Total impressions served.")
    conversions: int = Field(default=0, ge=0, description="Total conversions achieved.")
    cost: float = Field(default=0.0, ge=0.0, description="Total spend in CNY (¥).")
    value_per_conversion: float = Field(
        default=DEFAULT_VALUE_PER_CONVERSION,
        ge=0.0,
        description="Revenue per conversion in CNY (¥).",
    )
    skill_id: str | None = Field(
        default=None,
        max_length=200,
        description="Optional pre-existing skill id to associate with the campaign.",
    )
    roi: float | None = Field(
        default=None,
        description="(conversions*value - cost) / cost when cost > 0; else None.",
    )

    # ---------- validators --------------------------------------------------

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v

    @model_validator(mode="before")
    @classmethod
    def _inject_roi_on_construction(cls, data: Any) -> Any:
        """Inject ROI from conversions/value/cost before the model builds.

        Accepts either a dict or a MarketingCampaign. If ROI is already
        explicitly set in the input, it is respected. Otherwise it is
        computed from the campaign's own numbers so the field is
        always consistent with the source data on initial construction.
        """
        if isinstance(data, cls):
            return data
        if isinstance(data, dict):
            d = dict(data)
            if "roi" not in d or d["roi"] is None:
                d["roi"] = _compute_roi(
                    d.get("conversions", 0),
                    d.get("cost", 0.0),
                    d.get("value_per_conversion", DEFAULT_VALUE_PER_CONVERSION),
                )
            return d
        return data

    @model_validator(mode="after")
    def _recompute_roi_on_assignment(self):
        """Keep ``roi`` in lock-step with conversions/cost/value.

        Runs after every construction AND after every field assignment
        (the Envelope base has ``validate_assignment=True``). Writes
        via ``object.__setattr__`` so we do not re-enter
        ``validate_assignment`` (which would loop).
        """
        new_roi = _compute_roi(
            self.conversions,
            self.cost,
            self.value_per_conversion,
        )
        if new_roi != self.roi:
            object.__setattr__(self, "roi", new_roi)
        return self

    # ---------- helpers -----------------------------------------------------

    @property
    def revenue(self) -> float:
        """Total revenue (conversions * value_per_conversion)."""
        return float(self.conversions) * float(self.value_per_conversion)

    @property
    def profit(self) -> float:
        """Revenue minus cost. May be negative."""
        return self.revenue - float(self.cost)

    def is_high_roi(self, threshold: float = DEFAULT_ROI_THRESHOLD) -> bool:
        """True iff ROI is defined and strictly greater than ``threshold``."""
        return self.roi is not None and self.roi > threshold


class SkillRecommendation(Envelope):
    """A recommendation to promote a high-ROI campaign into a reusable skill.

    The audit_log is non-empty so the operator can verify *why* this
    recommendation was emitted (no silent promotion).
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    campaign_id: str = Field(..., min_length=1, description="Source MarketingCampaign id.")
    skill_id: str = Field(..., min_length=1, description="Materialised skill id.")
    campaign_name: str = Field(..., min_length=1, description="Source campaign name (denormalised).")
    channel: Channel = Field(..., description="Source campaign channel (denormalised).")
    roi: float = Field(..., description="ROI at the moment of recommendation.")
    impressions: int = Field(..., ge=0)
    conversions: int = Field(..., ge=0)
    cost: float = Field(..., ge=0.0)
    reason: str = Field(default="", description="Human-readable reason (audit-friendly).")
    audit_log: list[str] = Field(default_factory=list, description="Non-empty audit trail.")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class MarketingFeedbackService:
    """Track marketing campaigns and recommend skill promotions.

    State:

      - ``_campaigns``: list of every campaign ``track_campaign`` has
        accepted, in insertion order.
      - ``_recommendations``: list of every SkillRecommendation emitted,
        in insertion order.

    The service is process-local (mirrors C006/C007 in-memory design).
    Phase D persistence is out of scope for D005.
    """

    def __init__(self) -> None:
        self._campaigns: list[MarketingCampaign] = []
        self._recommendations: list[SkillRecommendation] = []
        self._recs_by_campaign: dict[str, SkillRecommendation] = {}

    # ---------- writes ------------------------------------------------------

    def track_campaign(self, campaign: MarketingCampaign) -> MarketingCampaign:
        """Track the ROI metrics of one campaign.

        Returns the campaign unchanged (its ``roi`` was already
        computed by the model validator). Appends to the internal
        list and emits a non-silent kernel log line.
        """
        self._campaigns.append(campaign)
        roi_str = "undefined" if campaign.roi is None else f"{campaign.roi:.4f}"
        logger.info(
            "track_campaign id=%s name=%s channel=%s roi=%s",
            campaign.id,
            campaign.name,
            campaign.channel.value,
            roi_str,
        )
        return campaign

    def recommend_skill_promotion(
        self,
        campaign: MarketingCampaign,
        *,
        threshold: float = DEFAULT_ROI_THRESHOLD,
    ) -> SkillRecommendation | None:
        """Recommend promotion if the campaign's ROI exceeds the threshold.

        Idempotent: a second call for the same campaign returns the
        existing recommendation rather than creating a duplicate.

        Returns ``None`` if the campaign's ROI is undefined (cost == 0)
        or below the threshold.
        """
        if campaign.roi is None:
            return None
        if campaign.roi <= threshold:
            return None
        existing = self._recs_by_campaign.get(campaign.id)
        if existing is not None:
            return existing

        skill_id = campaign.skill_id or f"skill_{campaign.channel.value}_{campaign.id[:8]}"
        now = utcnow()
        rec = SkillRecommendation(
            campaign_id=campaign.id,
            skill_id=skill_id,
            campaign_name=campaign.name,
            channel=campaign.channel,
            roi=campaign.roi,
            impressions=campaign.impressions,
            conversions=campaign.conversions,
            cost=campaign.cost,
            reason=(
                f"ROI {campaign.roi:.4f} exceeds threshold {threshold:.4f}"
            ),
            audit_log=[
                f"recommended_at={now.isoformat()}",
                f"roi={campaign.roi:.6f}",
                f"threshold={threshold:.6f}",
                f"channel={campaign.channel.value}",
                f"conversions={campaign.conversions}",
                f"cost={campaign.cost}",
            ],
        )
        self._recommendations.append(rec)
        self._recs_by_campaign[campaign.id] = rec
        return rec

    # ---------- reads -------------------------------------------------------

    def get_campaigns(self) -> list[MarketingCampaign]:
        """Return a copy of the tracked campaigns (insertion order)."""
        return list(self._campaigns)

    def get_recommendations(self) -> list[SkillRecommendation]:
        """Return a copy of the emitted recommendations (insertion order)."""
        return list(self._recommendations)

    def count_campaigns(self) -> int:
        return len(self._campaigns)

    def count_recommendations(self) -> int:
        return len(self._recommendations)


__all__ = [
    "Channel",
    "DEFAULT_VALUE_PER_CONVERSION",
    "DEFAULT_ROI_THRESHOLD",
    "MarketingCampaign",
    "SkillRecommendation",
    "MarketingFeedbackService",
]