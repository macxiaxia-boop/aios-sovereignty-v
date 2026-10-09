"""claude_code_adapter.py — Claude Code adapter (FIXED v2 — handles nested env).

Writes:
- ~/.cc-switch/cc-switch.db settings.common_config_claude.env sub-key ONLY
  (preserves permissions, skillOverrides, hooks etc. that cc-switch also stores there)

Does NOT write:
- ~/.claude/settings.json (FROZEN · _meta.modify_protocol requires ask_user)
- ~/.claude/CLAUDE.md (Moon Capsule L0 Kernel · R362)
- ~/.claude/.mcp.json (user-managed)
- ~/.claude/hooks.json
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .adapter_base import DriftReport, ModelPolicyAdapter
from .snapshot import PolicySnapshot


class ClaudeCodeAdapter(ModelPolicyAdapter):
    name = "claude-code"

    def __init__(
        self,
        settings_json_path: Optional[Path] = None,
        cc_switch_db_path: Optional[Path] = None,
    ):
        self.settings_json_path = settings_json_path or (Path.home() / ".claude" / "settings.json")
        self.cc_switch_db_path = cc_switch_db_path or (Path.home() / ".cc-switch" / "cc-switch.db")

    def current_state(self) -> dict:
        state = {
            "settings_env": {},
            "settings_frozen": False,
            "common_config_claude": "",
            "common_config_claude_parsed": {},
            "common_config_claude_env": {},
            "current_provider_claude": None,
        }
        if self.settings_json_path.exists():
            try:
                s = json.loads(self.settings_json_path.read_text(encoding="utf-8"))
                state["settings_env"] = s.get("env", {})
                state["settings_frozen"] = bool(s.get("_meta", {}).get("frozen_at"))
            except Exception as e:
                state["settings_error"] = str(e)
        if self.cc_switch_db_path.exists():
            try:
                db = sqlite3.connect(str(self.cc_switch_db_path))
                db.row_factory = sqlite3.Row
                cur = db.cursor()
                cur.execute("SELECT value FROM settings WHERE key = ?", ("common_config_claude",))
                row = cur.fetchone()
                state["common_config_claude"] = row["value"] if row else ""
                if state["common_config_claude"]:
                    try:
                        parsed = json.loads(state["common_config_claude"])
                        state["common_config_claude_parsed"] = parsed
                        if isinstance(parsed, dict):
                            state["common_config_claude_env"] = parsed.get("env", {})
                    except Exception:
                        pass
                cur.execute("SELECT value FROM settings WHERE key = ?", ("currentProviderClaude",))
                row = cur.fetchone()
                state["current_provider_claude"] = row["value"] if row else None
                db.close()
            except Exception as e:
                state["cc_switch_error"] = str(e)
        return state

    def _iter_env_items(self, env_dict: dict):
        """Yield (key, value) for env-like entries, recursing 1 level into env subkey."""
        if "env" in env_dict and isinstance(env_dict["env"], dict):
            for k, v in env_dict["env"].items():
                yield ("env." + k, v)
        for k, v in env_dict.items():
            if k != "env" and isinstance(v, str):
                yield (k, v)

    def verify(self, policy: PolicySnapshot) -> DriftReport:
        state = self.current_state()
        drift_paths = []
        kind = "none"
        severity = "ok"
        action = "ignore"

        env = state.get("settings_env", {})
        for k in ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
                  "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
                  "CLAUDE_CODE_SUBAGENT_MODEL"):
            v = env.get(k, "")
            if v and v in policy.denylist:
                kind = "fallback_injection"
                severity = "warn"  # settings.json frozen
                action = "warn"
                drift_paths.append(f"claude.settings.env.{k}:{v}")

        parsed = state.get("common_config_claude_parsed", {})
        if parsed:
            # Check nested env AND any string values at top level
            for k, v in self._iter_env_items(parsed):
                if isinstance(v, str) and v in policy.denylist:
                    if severity != "fail_closed":
                        kind = "fallback_injection"
                        severity = "fail_closed"
                        action = "revert"
                    drift_paths.append(f"cc_switch.settings.common_config_claude.{k}:{v}")

        cur_provider = state.get("current_provider_claude", "")
        if cur_provider in ("default",):
            if severity != "fail_closed":
                kind = "provider_drift"
                severity = "warn"
                action = "warn"
            drift_paths.append(f"cc_switch.settings.currentProviderClaude:{cur_provider}")

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

        if not dry_run and drift.recommended_action == "revert":
            try:
                # Read current full structure (preserve permissions, hooks, etc.)
                parsed = drift.details.get("common_config_claude_parsed", {})
                if not isinstance(parsed, dict):
                    parsed = {}

                # Build new env sub-key from policy enforcement
                new_env_cfg = policy.enforcement.get("cc_switch", {}).get(
                    "common_config_claude", {}
                )
                # Strip any "env." prefix from policy keys
                clean_env = {}
                for k, v in new_env_cfg.items():
                    if k.startswith("env."):
                        clean_env[k[4:]] = v
                    else:
                        clean_env[k] = v

                # Merge: replace env sub-key, preserve everything else
                parsed["env"] = clean_env

                new_value = json.dumps(parsed, indent=2)
                db = sqlite3.connect(str(self.cc_switch_db_path))
                cur = db.cursor()
                cur.execute("DELETE FROM settings WHERE key = ?", ("common_config_claude",))
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    ("common_config_claude", new_value),
                )
                db.commit()
                db.close()
                drift.details["applied_at"] = "common_config_claude.env (preserved permissions/hooks)"
            except Exception as e:
                drift.details["apply_error"] = str(e)

        return drift
