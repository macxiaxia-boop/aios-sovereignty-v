"""reconciler.py — ModelPolicy reconciler coordinator + CLI entry point.

Reads model-policy.v1.yaml, runs all 4 adapters, returns aggregate DriftReport.

CLI:
    python -m aios_kernel.governance.model_policy.reconciler --mode scheduled [--dry-run]
    python -m aios_kernel.governance.model_policy.reconciler --mode daemon --interval 30

Modes:
    scheduled  → invoked by AIOS_Sovereignty_Reconcile_5min Task Scheduler (5min tick)
    onstart    → invoked by PowerShell profile hook
    daemon     → invoked by WinSW service (v2, --interval 30s loop)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
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


def aggregate_severity_of(reports: List[DriftReport]) -> str:
    agg = "ok"
    for r in reports:
        if r.severity == "fail_closed":
            return "fail_closed"
        if r.severity == "warn" and agg == "ok":
            agg = "warn"
    return agg


def emit_json(policy: PolicySnapshot, mode: str, dry_run: bool, reports: List[DriftReport]) -> None:
    agg = aggregate_severity_of(reports)
    out = {
        "policy_id": policy.policy_id,
        "mode": mode,
        "dry_run": dry_run,
        "aggregate_severity": agg,
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


def emit_text(reports: List[DriftReport]) -> None:
    for r in reports:
        print(
            f"[{r.adapter_name}] drift={r.drift_kind} "
            f"severity={r.severity} action={r.recommended_action} "
            f"paths={len(r.affected_paths)}"
        )


def run_once(args, policy) -> int:
    reports = reconcile(policy, dry_run=args.dry_run)
    if args.json:
        emit_json(policy, args.mode, args.dry_run, reports)
    else:
        emit_text(reports)
    return 0 if aggregate_severity_of(reports) != "fail_closed" else 1


def run_daemon(args) -> int:
    sys.stderr.write(
        f"[reconciler/daemon] loop mode: interval={args.interval}s policy_id="
        f"{load_policy(Path(args.policy), Path(args.pub_key)).policy_id}\n"
    )
    while True:
        try:
            policy = load_policy(Path(args.policy), Path(args.pub_key))
        except Exception as e:
            sys.stderr.write(f"[reconciler/daemon] reload error: {e}\n")
            time.sleep(args.interval)
            continue
        try:
            reports = reconcile(policy, dry_run=args.dry_run)
            agg = aggregate_severity_of(reports)
            sys.stderr.write(f"[reconciler/daemon] tick: {agg}\n")
        except Exception as e:
            sys.stderr.write(f"[reconciler/daemon] tick error: {e}\n")
        time.sleep(args.interval)


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
    parser.add_argument(
        "--interval", type=int, default=0,
        help="Daemon mode loop interval in seconds (0 = one-shot)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    args = parser.parse_args(argv)

    if args.mode == "daemon" and args.interval > 0:
        return run_daemon(args)

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

    return run_once(args, policy)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
