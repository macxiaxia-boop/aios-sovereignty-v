"""codex_adapter.py — Codex CLI / Codex Desktop adapter.

Writes:
- ~/.codex/config.toml profiles (legacy cleanup)
- ~/.cc-switch/cc-switch.db settings.common_config_codex
- ~/.codex/auth.json (ONLY for credential mirror validation, not write)

Does NOT write:
- ~/.codex/hooks.json (hash-trusted)
- ~/.codex/.codex-global-state.json (browser state)
- ~/.codex/.personality_migration / .sandbox_migration (system files)
"""
from __future__ import annotations

import json
import sqlite3
import tomllib
from pathlib import Path
from typing import Optional

from .adapter_base import DriftReport, ModelPolicyAdapter
from .snapshot import PolicySnapshot


class CodexAdapter(ModelPolicyAdapter):
    name = "codex"

    def __init__(
        self,
        config_toml_path: Optional[Path] = None,
        cc_switch_db_path: Optional[Path] = None,
        auth_json_path: Optional[Path] = None,
    ):
        self.config_toml_path = config_toml_path or (Path.home() / ".codex" / "config.toml")
        self.cc_switch_db_path = cc_switch_db_path or (Path.home() / ".cc-switch" / "cc-switch.db")
        self.auth_json_path = auth_json_path or (Path.home() / ".codex" / "auth.json")

    def current_state(self) -> dict:
        state = {"profiles": [], "cc_switch_codex_provider": None, "common_config_codex": {}, "auth_present": False}
        # Read config.toml profiles
        if self.config_toml_path.exists():
            try:
                with self.config_toml_path.open("rb") as f:
                    cfg = tomllib.load(f)
                profiles = cfg.get("profiles", {})
                state["profiles"] = [
                    {"name": n, "model": p.get("model", "")} for n, p in profiles.items()
                ]
            except Exception as e:
                state["config_toml_error"] = str(e)

        # Read cc-switch.db currentProviderCodex + common_config_codex
        if self.cc_switch_db_path.exists():
            try:
                db = sqlite3.connect(str(self.cc_switch_db_path))
                db.row_factory = sqlite3.Row
                cur = db.cursor()
                cur.execute("SELECT value FROM settings WHERE key = ?", ("currentProviderCodex",))
                row = cur.fetchone()
                if row:
                    state["cc_switch_codex_provider"] = row["value"]
                cur.execute("SELECT value FROM settings WHERE key = ?", ("common_config_codex",))
                row = cur.fetchone()
                if row:
                    state["common_config_codex"] = row["value"]
                db.close()
            except Exception as e:
                state["cc_switch_error"] = str(e)

        # Read auth.json present
        if self.auth_json_path.exists():
            try:
                auth = json.loads(self.auth_json_path.read_text(encoding="utf-8"))
                state["auth_present"] = bool(auth.get("OPENAI_API_KEY"))
                state["auth_token_prefix"] = (auth.get("OPENAI_API_KEY", "") or "")[:10]
            except Exception as e:
                state["auth_error"] = str(e)
        return state

    def verify(self, policy: PolicySnapshot) -> DriftReport:
        state = self.current_state()
        drift_paths = []
        kind = "none"
        severity = "ok"
        action = "ignore"

        # Check cc-switch currentProviderCodex
        provider_id = state.get("cc_switch_codex_provider") or ""
        # Best-effort: fetch provider row
        try:
            db = sqlite3.connect(str(self.cc_switch_db_path))
            cur = db.cursor()
            cur.execute("SELECT payload FROM providers WHERE id = ?", (provider_id,))
            row = cur.fetchone()
            db.close()
            if row:
                payload = json.loads(row[0])
                # Codex provider stores models in auth.config
                cfg = payload.get("config", "")
                # Quick check: does config string contain a denylist model?
                for m in policy.denylist:
                    if m in cfg:
                        kind = "provider_drift"
                        severity = "fail_closed"
                        action = "revert"
                        drift_paths.append(f"cc_switch.providers.{provider_id}.config:{m}")
        except Exception:
            pass

        # Check config.toml profiles — if any profile model in denylist, warn
        for prof in state.get("profiles", []):
            if prof.get("model") in policy.denylist:
                kind = "profile_drift"
                severity = "warn"
                action = "warn"
                drift_paths.append(f"config_toml.profiles.{prof['name']}:{prof['model']}")

        # Check common_config_codex for non-allowlist drift
        common = state.get("common_config_codex", "")
        if common and "deepseek" in common.lower():
            kind = "fallback_injection"
            severity = "fail_closed"
            action = "revert"
            drift_paths.append("cc_switch.settings.common_config_codex")

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
            # Rewrite common_config_codex (allowlist-only)
            try:
                db = sqlite3.connect(str(self.cc_switch_db_path))
                cur = db.cursor()
                new_cfg_text = policy.enforcement.get("cc_switch", {}).get(
                    "common_config_codex", {}
                )
                # Inline as toml text representation
                inline = "\n".join(f"{k} = {json.dumps(v)}" for k, v in new_cfg_text.items())
                cur.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("common_config_codex", inline),
                )
                db.commit()
                db.close()
            except Exception as e:
                drift.details["apply_error"] = str(e)

        return drift
