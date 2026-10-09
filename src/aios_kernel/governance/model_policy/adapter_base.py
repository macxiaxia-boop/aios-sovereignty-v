"""adapter_base.py — ModelPolicy adapter interface + DriftReport.

Each adapter (Codex / Claude Code / OpenClaw / Hermes) implements:
- name: str
- current_state() -> dict
- verify(policy) -> DriftReport
- apply(policy, dry_run) -> DriftReport

DriftReport.severity:
- "fail_closed" → adapter must revert immediately
- "warn"        → adapter logs but does not revert
- "ok"          → no drift

DriftReport.recommended_action:
- "revert"      → write to restore
- "warn"        → write a warning event
- "ignore"      → silent
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .snapshot import PolicySnapshot


@dataclass
class DriftReport:
    adapter_name: str
    drift_kind: str = "none"            # "fallback_injection" | "profile_drift" | "provider_drift" | "missing_policy_table" | "none"
    severity: str = "ok"                 # "fail_closed" | "warn" | "ok"
    affected_paths: List[str] = field(default_factory=list)
    recommended_action: str = "ignore"   # "revert" | "warn" | "ignore"
    details: Dict = field(default_factory=dict)


class ModelPolicyAdapter(ABC):
    """Abstract base for all 4 adapters."""

    name: str = "abstract"

    @abstractmethod
    def current_state(self) -> dict:
        """Read current model configuration on this end."""

    @abstractmethod
    def verify(self, policy: PolicySnapshot) -> DriftReport:
        """Read current state, compare against policy, return DriftReport (no writes)."""

    @abstractmethod
    def apply(self, policy: PolicySnapshot, dry_run: bool = False) -> DriftReport:
        """Apply policy to this end. Return DriftReport describing action taken."""
