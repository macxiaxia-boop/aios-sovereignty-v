"""reconciler.py — ModelPolicy reconciler coordinator + CLI entry point.

Reads model-policy.v1.yaml, runs all 4 adapters, returns aggregate DriftReport.

CLI:
    python -m aios_kernel.governance.model_policy.reconciler --mode scheduled [--dry-run]

Modes:
    scheduled  → invoked by AIOS_Sovereignty_Reconcile_5min Task Scheduler
    onstart    → invoked by PowerShell profile hook
    daemon     → invoked by WinSW service (v2)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List

from .adapter_base import DriftReport
from .claude_code_adapter import ClaudeCodeAdapter
from .codex_adapter import CodexAdapter
from .hermes_adapter import HermesAdapter
from .openclaw_adapter import OpenClawAdapter
from .snapshot import PolicySnapshot, load_policy


DEFAULT_POLICY_PATH = Path(r"D:\AIOS\kernel\etc\sovereignty\model-policy.v1.yaml")
DEFAULT_PUB_KEY_PATH = Path(r"D:\AIOS\kernel\etc\sovereignty\codex_supervisor.ed25519.pub")


def build_default_adapters() -> list:
    """Construct the 4 adapters with default paths."""
    return [
        CodexAdapter(),
        ClaudeCodeAdapter(),
        OpenClawAdapter(),
        HermesAdapter(),
    ]


def reconcile(policy: PolicySnapshot, adapters: list = None, dry_run: bool = False) -> List[DriftReport]:
    """Run all adapters' verify+apply. Returns list of DriftReport."""
    if adapters is None:
        adapters = build_default_adapters()
    reports = []
    for adapter in adapters:
        try:
            drift = adapter.apply(policy, dry_run=dry_run)
        except Exception as e:
            drift = DriftReport(
                adapter_name=adapter.name,
                drift_kind="adapter_error",
                severity="warn",
                affected_paths=[adapter.name],
                recommended_action="warn",
                details={"error": str(e)},
            )
        reports.append(drift)
    return reports


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aios_kernel.governance.model_policy.reconciler",
        description="AIOS-SOVEREIGNTY-V Reconciler",
    )
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--pub-key", default=str(DEFAULT_PUB_KEY_PATH))
    parser.add_argument(
        "--mode",
        choices=["scheduled", "onstart", "daemon"],
        default="scheduled",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    args = parser.parse_args(argv)

    try:
        policy = load_policy(Path(args.policy), Path(args.pub_key))
    except Exception as e:
        sys.stderr.write(f"ERROR loading policy: {e}\n")
        return 2

    sys.stderr.write(
        f"[reconciler/{args.mode}] policy_id={policy.policy_id} "
        f"allow={len(policy.allowlist)} deny={len(policy.denylist)} "
        f"optional={len(policy.optional)} dry_run={args.dry_run}\n"
    )

    reports = reconcile(policy, dry_run=args.dry_run)
    aggregate_severity = "ok"
    for r in reports:
        if r.severity == "fail_closed":
            aggregate_severity = "fail_closed"
            break
        if r.severity == "warn" and aggregate_severity == "ok":
            aggregate_severity = "warn"

    if args.json:
        out = {
            "policy_id": policy.policy_id,
            "mode": args.mode,
            "dry_run": args.dry_run,
            "aggregate_severity": aggregate_severity,
            "reports": [
                {
                    "adapter": r.adapter_name,
                    "drift_kind": r.drift_kind,
                    "severity": r.severity,
                    "recommended_action": r.recommended_action,
                    "affected_paths": r.affected_paths,
                }
                for r in reports
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        for r in reports:
            print(
                f"[{r.adapter_name}] drift={r.drift_kind} "
                f"severity={r.severity} action={r.recommended_action} "
                f"paths={len(r.affected_paths)}"
            )

    return 0 if aggregate_severity != "fail_closed" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
