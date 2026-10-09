"""openclaw_adapter.py — OpenClaw adapter.

Writes:
- ~/.openclaw/state/openclaw.sqlite policy_allowlist table (CREATE + INSERT)
- ~/.openclaw/etc/policy.yaml (mirror for ops visibility)
- ~/.openclaw/.env (env_keys validation only; does NOT write token)

Does NOT write:
- 9 agent sub-databases (per-agent decisions)
- workspace-*/ project files
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

from .adapter_base import DriftReport, ModelPolicyAdapter
from .snapshot import PolicySnapshot


class OpenClawAdapter(ModelPolicyAdapter):
    name = "openclaw"

    def __init__(
        self,
        openclaw_db_path: Optional[Path] = None,
        policy_yaml_path: Optional[Path] = None,
        env_path: Optional[Path] = None,
    ):
        self.openclaw_db_path = openclaw_db_path or (Path.home() / ".openclaw" / "state" / "openclaw.sqlite")
        self.policy_yaml_path = policy_yaml_path or (Path.home() / ".openclaw" / "etc" / "policy.yaml")
        self.env_path = env_path or (Path.home() / ".openclaw" / ".env")

    def _ensure_policy_table(self, db: sqlite3.Connection) -> None:
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS policy_allowlist (
                policy_id TEXT,
                model_id TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                UNIQUE(policy_id, model_id)
            )
        """)
        db.commit()

    def current_state(self) -> dict:
        state = {"policy_allowlist_count": 0, "policy_allowlist_models": [], "env_keys_present": []}
        if self.openclaw_db_path.exists():
            try:
                db = sqlite3.connect(str(self.openclaw_db_path))
                cur = db.cursor()
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='policy_allowlist'"
                )
                if cur.fetchone():
                    cur.execute("SELECT model_id, category FROM policy_allowlist")
                    rows = cur.fetchall()
                    state["policy_allowlist_count"] = len(rows)
                    state["policy_allowlist_models"] = [{"id": r[0], "category": r[1]} for r in rows]
                db.close()
            except Exception as e:
                state["db_error"] = str(e)
        if self.env_path.exists():
            try:
                for line in self.env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k = line.split("=", 1)[0].strip()
                        state["env_keys_present"].append(k)
            except Exception as e:
                state["env_error"] = str(e)
        return state

    def verify(self, policy: PolicySnapshot) -> DriftReport:
        state = self.current_state()
        drift_paths = []
        # Severity/action escalate: ok → warn → fail_closed; revert vs warn
        kind = "none"
        severity = "ok"
        action = "ignore"

        existing_models = {m["id"] for m in state["policy_allowlist_models"]}
        expected = set(policy.allowlist) | set(policy.optional)

        missing = expected - existing_models
        if missing:
            kind = "missing_policy_table"
            severity = "fail_closed"
            action = "revert"
            drift_paths.append(f"openclaw.policy_allowlist.missing:{sorted(missing)}")

        bad = existing_models & set(policy.denylist)
        if bad:
            kind = "policy_drift"
            severity = "fail_closed"
            action = "revert"
            drift_paths.append(f"openclaw.policy_allowlist.denylisted:{sorted(bad)}")

        env_keys_required = []
        for p in policy.providers:
            env_keys_required.extend(p.get("auth", {}).get("env_keys", []))
        env_present = set(state["env_keys_present"])
        env_missing = set(env_keys_required) - env_present
        if env_missing:
            # Credential warn does NOT downgrade a fail_closed severity
            drift_paths.append(f"openclaw.env.missing:{sorted(env_missing)}")
            if severity != "fail_closed":
                kind = "credential_drift"
                severity = "warn"
                action = "warn"
            # else: keep fail_closed

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
                self.policy_yaml_path.parent.mkdir(parents=True, exist_ok=True)
                db = sqlite3.connect(str(self.openclaw_db_path))
                self._ensure_policy_table(db)
                cur = db.cursor()
                cur.execute("DELETE FROM policy_allowlist WHERE policy_id = ?", (policy.policy_id,))
                now = int(os.path.getmtime(self.openclaw_db_path))
                for m in policy.allowlist:
                    cur.execute(
                        "INSERT OR IGNORE INTO policy_allowlist (policy_id, model_id, category, created_at) VALUES (?, ?, ?, ?)",
                        (policy.policy_id, m, "allowlist", now),
                    )
                for m in policy.optional:
                    cur.execute(
                        "INSERT OR IGNORE INTO policy_allowlist (policy_id, model_id, category, created_at) VALUES (?, ?, ?, ?)",
                        (policy.policy_id, m, "optional", now),
                    )
                db.commit()
                db.close()
                yaml_text = json.dumps(
                    {
                        "policy_id": policy.policy_id,
                        "allowlist": policy.allowlist,
                        "denylist": policy.denylist,
                        "optional": policy.optional,
                        "synced_at": now,
                    },
                    indent=2,
                )
                self.policy_yaml_path.write_text(yaml_text, encoding="utf-8")
            except Exception as e:
                drift.details["apply_error"] = str(e)

        return drift
