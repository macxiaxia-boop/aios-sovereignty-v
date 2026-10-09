"""hermes_adapter.py — Hermes CLI adapter.

Hermes is CLI-on-demand (no daemon). The adapter writes:
- ~/.hermes/cli-config.yaml (model.provider_first + provider_denylist)

Does NOT write:
- hermes-agent/providers/*.py (Python code)
- ~/.hermes/hermes-agent/gateway/* (gateway)
- ~/.hermes/gateway-service/hermes-gateway.cmd (WinSW launcher)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from .adapter_base import DriftReport, ModelPolicyAdapter
from .snapshot import PolicySnapshot


class HermesAdapter(ModelPolicyAdapter):
    name = "hermes"

    def __init__(self, cli_config_path: Optional[Path] = None):
        self.cli_config_path = cli_config_path or (Path.home() / ".hermes" / "cli-config.yaml")

    def current_state(self) -> dict:
        state = {"cli_config_provider": "", "cli_config_default": "", "exists": False}
        if self.cli_config_path.exists():
            state["exists"] = True
            try:
                cfg = yaml.safe_load(self.cli_config_path.read_text(encoding="utf-8")) or {}
                m = cfg.get("model", {})
                state["cli_config_provider"] = m.get("provider", "")
                state["cli_config_default"] = m.get("default", "")
            except Exception as e:
                state["yaml_error"] = str(e)
        return state

    def verify(self, policy: PolicySnapshot) -> DriftReport:
        state = self.current_state()
        drift_paths = []
        kind = "none"
        severity = "ok"
        action = "ignore"

        # Hermes provider strings: minimax / minimax-cn are canonical
        provider_first = policy.enforcement.get("hermes", {}).get(
            "cli_config_provider_first", ["minimax", "minimax-cn"]
        )
        provider_deny = policy.enforcement.get("hermes", {}).get(
            "cli_config_provider_denylist", []
        )

        cur = state.get("cli_config_provider", "")
        # Provider must be in provider_first or "auto"
        if cur and cur != "auto" and cur not in provider_first:
            if cur in provider_deny:
                kind = "provider_drift"
                severity = "warn"  # Hermes is CLI-on-demand; just warn
                action = "warn"
                drift_paths.append(f"hermes.cli_config.model.provider:{cur}")
            else:
                kind = "provider_drift"
                severity = "warn"
                action = "warn"
                drift_paths.append(f"hermes.cli_config.model.provider:{cur}")

        return DriftReport(
            adapter_name=self.name,
            drift_kind=kind,
            severity=severity,
            affected_paths=drift_paths,
            recommended_action=action,
            details=state,
        )

    def apply(self, policy: PolicySnapshot, dry_run: bool = False) -> DriftReport:
        drift = self.verify(policy)
        if drift.severity == "ok":
            return drift

        # Hermes write only happens if user has cli-config.yaml AND wants policy enforced.
        # v1: only log warn, do not auto-write (Hermes is user-managed CLI tool).
        # v2: could write provider_first + provider_denylist arrays into cli-config.
        drift.details["policy_hint"] = (
            f"To enforce, set model.provider to one of: "
            f"{policy.enforcement.get('hermes', {}).get('cli_config_provider_first', ['minimax'])}"
        )
        return drift
