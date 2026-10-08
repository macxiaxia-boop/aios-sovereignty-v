"""aios_kernel.business — Phase D (Business Intelligence) modules.

Modules (D002-D006):
- marketing_feedback: D005 — Marketing campaign ROI tracking + skill
  promotion recommendation (high-ROI campaigns become reusable skills).
"""
from aios_kernel.business.marketing_feedback import (
    DEFAULT_ROI_THRESHOLD,
    DEFAULT_VALUE_PER_CONVERSION,
    Channel,
    MarketingCampaign,
    MarketingFeedbackService,
    SkillRecommendation,
)

__all__ = [
    "Channel",
    "DEFAULT_VALUE_PER_CONVERSION",
    "DEFAULT_ROI_THRESHOLD",
    "MarketingCampaign",
    "MarketingFeedbackService",
    "SkillRecommendation",
]