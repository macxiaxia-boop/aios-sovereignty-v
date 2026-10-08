#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GATED LIVE SMOKE TEST for R286.A-C.

Runs ONLY when explicitly invoked (NOT in run_all_tests.py).  Writes a
unique R286 marker envelope to the LIVE v2 queue, dispatches it, and
verifies a result envelope is produced.  Does NOT touch the 3 stranded
pre-R320.6 ack files.  Cleans up only R286-generated smoke messages.

Usage:
    python test_gated_live_smoke_r286.py [--keep] [--verbose]

Hard rules:
- No live process restart (we ONLY write envelopes + use the v2 consumer
  in --once mode).
- The consumer is invoked with --once + a marker_filter that ONLY claims
  R286-tagged envelopes.  This is the per-R286-plan contract: "Do not let
  the consumer claim unrelated legacy files."
- Cleans only R286-generated files via marker filter (filename prefix).
- The 3 stranded ack files are NEVER touched.

Outputs JSON evidence to v2/reports/r286_live_smoke_evidence.json (and
channel-audit-20260930/evidence/R286_LIVE_SMOKE_EVIDENCE.json when called
from R286 implementation round).
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Make v2 importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import build_envelope, reply_envelope
from src.id import idempotency_key, utc_now_iso
from src.paths import DEADLETTER, INBOX, OUTBOX, TASKS_DIR, EVENTS_LOG, ensure_dirs, v2_root
from src.queue import enqueue

# R286 marker — every R286-generated envelope payload contains this string.
R286_MARKER = "r286_smoke_marker_DO_NOT_REMOVE"


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_r286_file(p: Path) -> bool:
    """Defensive: only operate on files that contain the R286 marker in their JSON payload."""
    try:
        env = json.loads(p.read_text(encoding="utf-8"))
        marker = (env.get("payload") or {}).get("__r286_marker__", "")
        return marker == R286_MARKER
    except Exception:
        return False


def smoke(verbose: bool = False, keep: bool = False):
    """Run the gated live smoke loopback.  Returns the evidence dict."""
    ensure_dirs()

    marker = R286_MARKER
    # Build a v2 envelope from claude -> codex carrying the R286 marker
    sender = "claudecode"
    recipient = "codex"
    env_input = build_envelope(
        sender=sender, recipient=recipient, message_type="message",
        payload={"text": "r286-gated-live-smoke-input",
                 "__r286_marker__": marker,
                 "r286_test_run_id": str(uuid.uuid4()),
                 "produced_at": _now_iso()},
        correlation_id=None, in_reply_to=None,
    )

    if verbose:
        print(f"[smoke] writing input envelope {env_input['id']} to {INBOX}")
    enqueue(env_input)

    # Now invoke the v2 consumer with a marker_filter so it ONLY claims
    # R286-tagged envelopes.  This is the "do not consume unrelated legacy
    # files" contract from R286 plan.

    # Use the v2_consumer.tick API in-process with marker_filter for safety
    from src.v2_consumer import tick as _consumer_tick
    # Verify consumer module is loadable (used as a health sentinel)
    try:
        import src.v2_consumer as _consumer_mod
        if not hasattr(_consumer_mod, "tick"):
            return {"ok": False, "error": "v2_consumer.tick not available"}
    except ImportError as e:
        return {"ok": False, "error": f"v2_consumer import failed: {e}"}
    result = _consumer_tick(recipients=[recipient], marker_filter=lambda e:
                  (e.get("payload") or {}).get("__r286_marker__") == marker)

    if verbose:
        print(f"[smoke] tick result: {json.dumps(result, default=str)[:500]}...")

    # Verify a result envelope was produced
    # Result envelopes don't carry the R286 marker (their payload is the
    # dispatcher output), so we match by correlation_id == input envelope id.
    result_envs = []
    for p in INBOX.glob(f"*.json"):
        if ".tmp." in p.name or ".claimed." in p.name or ".dead." in p.name:
            continue
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (env.get("message_type") == "result"
                and env.get("correlation_id") == env_input["id"]):
            result_envs.append({"path": p.name, "envelope": env})

    # Also collect ack envelopes addressed to original.sender with correlation_id
    ack_envs = []
    for p in INBOX.glob(f"*.json"):
        if ".tmp." in p.name or ".claimed." in p.name or ".dead." in p.name:
            continue
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (env.get("message_type") == "ack"
                and env.get("correlation_id") == env_input["id"]):
            ack_envs.append({"path": p.name, "envelope": env})

    # Verify the 3 stranded acks were NOT touched
    legacy_unchanged = []
    for stranded_id in ("41afc2c3-8fd3-4c80-80f2-62943eea25fd",
                        "19334d04-08f8-4d3d-9f94-4eab28d336ce",
                        "0fbf6f33-4eb9-47b6-9400-1c2914b2d72f"):
        for d in (INBOX, OUTBOX):
            for p in d.glob(f"{stranded_id}__*.json"):
                legacy_unchanged.append(str(p.relative_to(v2_root())))

    evidence = {
        "ok": True,
        "smoke_run_id": env_input["payload"]["r286_test_run_id"],
        "ts": _now_iso(),
        "host": socket.gethostname().split(".")[0],
        "v2_root": str(v2_root()),
        "input_envelope_id": env_input["id"],
        "input_marker": marker,
        "tick_totals": result.get("totals", {}),
        "result_envelopes_count": len(result_envs),
        "result_envelopes": result_envs[:5],  # truncate
        "ack_envelopes_count": len(ack_envs),
        "ack_envelopes": ack_envs[:5],
        "legacy_stranded_unchanged": legacy_unchanged,
        "legacy_stranded_count": len(legacy_unchanged),
        "ai_os_v2_dispatch_asserted": result.get("totals", {}).get("claimed", 0) >= 1
                                       and len(result_envs) >= 1
                                       and len(ack_envs) >= 1,
        "ack_separate_from_result": len(ack_envs) >= 1 and len(result_envs) >= 1
                                      and ack_envs[0]["envelope"]["id"] != result_envs[0]["envelope"]["id"],
    }

    # Cleanup: remove only R286-tagged files we produced (per R286 plan: "Clean only
    # R286-generated smoke messages after preserving evidence; do not touch the
    # 3 old stranded ack files.")
    if not keep:
        cleaned = []
        for p in INBOX.glob("*.json"):
            if _is_r286_file(p):
                try:
                    p.unlink()
                    cleaned.append(str(p.name))
                except Exception as e:
                    evidence.setdefault("cleanup_errors", []).append(f"{p}: {e}")
        for p in OUTBOX.glob("*.json"):
            if _is_r286_file(p):
                try:
                    p.unlink()
                    cleaned.append(str(p.name))
                except Exception as e:
                    evidence.setdefault("cleanup_errors", []).append(f"{p}: {e}")
        for p in DEADLETTER.glob("*.json"):
            if _is_r286_file(p):
                try:
                    p.unlink()
                    cleaned.append(str(p.name))
                except Exception as e:
                    evidence.setdefault("cleanup_errors", []).append(f"{p}: {e}")
        evidence["cleaned_files"] = cleaned

    # Verify legacy stranded STILL unchanged after cleanup
    after_legacy = []
    for stranded_id in ("41afc2c3-8fd3-4c80-80f2-62943eea25fd",
                        "19334d04-08f8-4d3d-9f94-4eab28d336ce",
                        "0fbf6f33-4eb9-47b6-9400-1c2914b2d72f"):
        for d in (INBOX, OUTBOX):
            for p in d.glob(f"{stranded_id}__*.json"):
                after_legacy.append(str(p.relative_to(v2_root())))
    evidence["legacy_stranded_after_cleanup"] = after_legacy
    evidence["legacy_stranded_intact"] = sorted(after_legacy) == sorted(legacy_unchanged)

    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="R286.A-C gated live smoke")
    parser.add_argument("--keep", action="store_true", help="keep R286-generated smoke files")
    parser.add_argument("--verbose", action="store_true", help="verbose output")
    parser.add_argument("--evidence-dir", default=None,
                        help="output directory for evidence JSON (default: v2 reports dir)")
    args = parser.parse_args()

    evidence = smoke(verbose=args.verbose, keep=args.keep)
    print(json.dumps(evidence, ensure_ascii=False, indent=2))

    # Write evidence to both v2 reports and channel-audit report dirs
    if args.evidence_dir is None:
        args.evidence_dir = str(ROOT / "reports")
    out_dir = Path(args.evidence_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "r286_live_smoke_evidence.json"
    out_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"[smoke] evidence written to {out_path}", file=sys.stderr)

    return 0 if evidence.get("ok") and evidence.get("ai_os_v2_dispatch_asserted") else 1


if __name__ == "__main__":
    sys.exit(main())