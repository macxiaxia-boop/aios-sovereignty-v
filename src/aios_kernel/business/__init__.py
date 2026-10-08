"""aios_kernel.business — Phase D (Business Intelligence) modules.

Modules (D002-D006):
- marketing_feedback: D005 — Marketing campaign ROI tracking + skill
  promotion recommendation (high-ROI campaigns become reusable skills).
"""
from aios_kernel.business.marketing_feedback import (
    Channel,
    MarketingCampaign,
    MarketingFeedbackService,
    SkillRecommendation,
)

__all__ = [
    "Channel",
    "MarketingCampaign",
    "MarketingFeedbackService",
    "SkillRecommendation",
]