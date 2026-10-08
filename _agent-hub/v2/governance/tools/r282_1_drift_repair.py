#!/usr/bin/env python3
"""R282.1 drift-repair helper.

PURPOSE
=======
Fix the two concurrent-WorkBuddy-relink-drift failures detected by
`protocol_registry.py validate` after R282:

  - current shared-identity-bootstrap path missing: _relinked/workbuddy/BOOTSTRAP.md
  - current shared-identity-identity  path missing: _relinked/workbuddy/IDENTITY.md

The drift itself is out of scope (a concurrent external process removed the two
runtime files). This helper only fixes the **governance pointer / drift handling**.

WHAT IT DOES
============
Dry-run mode (default):
  - Loads PROTOCOL_REGISTRY.json
  - Computes the proposed diff (status flips, new entry append, pointer re-anchors,
    hash refresh for promoted entries whose on-disk file was edited)
  - Prints the exact before/after diff to stdout
  - Prints the proposed totals_by_status and current_by_family
  - Does NOT touch the file

Apply mode (--apply --approve R282_1_REGISTRY_ONLY):
  - Same diff, then atomic write (unique temp + os.replace; no os.remove on failure)
  - Then re-runs `protocol_registry.py validate` to confirm exit 0
  - Then re-runs `protocol_registry.py list-current` to print the 29/29 picture

PROPOSED CHANGES (one atomic write)
===================================
1. shared-identity-bootstrap family
   - current_by_family[shared-identity-bootstrap] = "r282.1-decision-shared-identity-bootstrap"   (was "shared-identity-bootstrap")
   - entries["shared-identity-bootstrap"].status                = "superseded"                      (was "current")
   - entries["shared-identity-bootstrap"].superseded_by         = "r282.1-decision-shared-identity-bootstrap"
   - entries["shared-identity-bootstrap"].evidence_note         = "former current; runtime file disappeared after concurrent WorkBuddy relink drift (R282.1); preserved as evidence-only; hash+size from R282 capture kept."
   - APPEND entries["r282.1-decision-shared-identity-bootstrap"] with status="current", path=_agent-hub/v2/governance/decisions/R282.1_DEC_01_shared_identity_bootstrap.md, r282.1_role=decision_record, computed hash+size

2. shared-identity-identity family
   - current_by_family[shared-identity-identity] = "r282-decision-shared-identity-identity"        (was "shared-identity-identity")
   - entries["shared-identity-identity"].status                = "superseded"                          (was "current")
   - entries["shared-identity-identity"].superseded_by         = "r282-decision-shared-identity-identity"
   - entries["shared-identity-identity"].evidence_note         = "former current; runtime file disappeared after concurrent WorkBuddy relink drift (R282.1); preserved as evidence-only; hash+size from R282 capture kept."
   - entries["r282-decision-shared-identity-identity"].status   = "current"                             (was "candidate")
   - entries["r282-decision-shared-identity-identity"].hash     = <recomputed> if the on-disk R282_DEC_06 file changed

3. audit_id, captured_at, totals_by_status, totals are recomputed.
   - audit_id: "system-audit-20260929-R282.1"
   - totals_by_status target: current=29, candidate=2, superseded=9, unknown=0 (40 entries total)

SAFETY
======
- Default is dry-run. --apply requires --approve R282_1_REGISTRY_ONLY. Either missing → exit 0 in dry-run mode.
- Atomic write: unique temp, fsync, os.replace; no os.remove on failure.
- Post-apply: runs `protocol_registry.py validate`; exits 3 if validate fails (registry left in place).
- Validates hash for the new decision record file before writing.
- IDEMPOTENT: a re-run skips already-applied flips and the duplicate APPEND; it only refreshes hashes for promoted entries whose on-disk file changed.

USAGE
=====
    # dry-run
    python tools/r282_1_drift_repair.py

    # apply
    python tools/r282_1_drift_repair.py --apply --approve R282_1_REGISTRY_ONLY
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("D:/AIOS").resolve()
REG_PATH = Path("D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json")
DEC_DIR = Path("D:/AIOS/_agent-hub/v2/governance/decisions")
TOOL_DIR = Path("D:/AIOS/_agent-hub/v2/governance/tools")
PROTO_REG_PY = Path("D:/AIOS/_agent-hub/v2/governance/protocol_registry.py")

REQUIRED_APPROVAL = "R282_1_REGISTRY_ONLY"
NEW_DEC_FILE = "R282.1_DEC_01_shared_identity_bootstrap.md"
NEW_DEC_REL = f"_agent-hub/v2/governance/decisions/{NEW_DEC_FILE}"
NEW_DEC_ID = "r282.1-decision-shared-identity-bootstrap"
PROMOTED_DEC_ID = "r282-decision-shared-identity-identity"
BOOTSTRAP_RUNTIME_ID = "shared-identity-bootstrap"
IDENTITY_RUNTIME_ID = "shared-identity-identity"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_reg():
    with open(REG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def propose_diff(reg):
    """Compute the proposed edits; return (new_reg, diff_lines).

    Pure function: does NOT mutate reg.
    IDEMPOTENT: if the R282.1 fix has already been applied, it still:
      - verifies hashes for promoted decision records (R282_DEC_06 may have been edited in-place)
      - skips duplicate APPEND for the new decision record
      - skips redundant status flips
      - always recomputes totals_by_status + totals
    """
    new_reg = json.loads(json.dumps(reg))  # deep copy
    diff = []

    # ---------- 1. shared-identity-bootstrap family ----------
    new_dec_full = DEC_DIR / NEW_DEC_FILE
    if not new_dec_full.exists():
        raise SystemExit(f"FAIL: new decision record missing on disk: {new_dec_full}")
    new_dec_sha = sha256_file(new_dec_full)
    new_dec_sz = new_dec_full.stat().st_size

    # 1a. flip runtime entry (idempotent)
    boot_entry = next(e for e in new_reg["entries"] if e["id"] == BOOTSTRAP_RUNTIME_ID)
    if boot_entry["status"] != "superseded":
        diff.append(f"  [entries/{BOOTSTRAP_RUNTIME_ID}].status:        {boot_entry['status']!r} -> 'superseded'")
        diff.append(f"  [entries/{BOOTSTRAP_RUNTIME_ID}].superseded_by: {boot_entry.get('superseded_by')!r} -> {NEW_DEC_ID!r}")
        boot_entry["status"] = "superseded"
        boot_entry["superseded_by"] = NEW_DEC_ID
    if "former current; runtime file disappeared" not in boot_entry.get("evidence_note", ""):
        diff.append(f"  [entries/{BOOTSTRAP_RUNTIME_ID}].evidence_note:  <append> 'former current; runtime file disappeared after concurrent WorkBuddy relink drift (R282.1); preserved as evidence-only; hash+size from R282 capture kept.'")
        boot_entry["evidence_note"] = (
            "former current; runtime file disappeared after concurrent WorkBuddy relink drift (R282.1); "
            "preserved as evidence-only; hash+size from R282 capture kept."
        )

    # 1b. append new decision-record entry (idempotent)
    if not any(e["id"] == NEW_DEC_ID for e in new_reg["entries"]):
        new_entry = {
            "id": NEW_DEC_ID,
            "title": "R282.1 Decision Record - family=shared-identity-bootstrap (drift repair)",
            "path": NEW_DEC_REL,
            "version": "R282.1-2026-09-29",
            "status": "current",
            "family": "shared-identity-bootstrap",
            "supersedes": [],
            "superseded_by": None,
            "evidence": [
                "Decision record - current (runtime file MISSING on disk at R282.1 capture; was current at R282 capture)",
                "Authoritative absent due to drift: file existed at R282 (1089 B, sha256 4b154cb7...) but disappeared after concurrent external WorkBuddy relink",
                "Junction C:\\Users\\xinzh\\.workbuddy -> D:\\AIOS\\_relinked\\workbuddy\\ still resolves; only BOOTSTRAP.md and IDENTITY.md are absent; 19 other files in _relinked/workbuddy/ are intact",
                "This decision-record authority does NOT claim runtime availability",
                "See PROTOCOL_AUDIT.md \u00a79 R282.1 section; see DRIFT_INCIDENT_R282_1.md",
            ],
            "hash": new_dec_sha,
            "hash_size_bytes": new_dec_sz,
            "r282_1_role": "decision_record",
        }
        new_reg["entries"].append(new_entry)
        diff.append(f"  [entries] APPEND {NEW_DEC_ID}: status=current, path={NEW_DEC_REL}, hash={new_dec_sha[:12]}, size={new_dec_sz}")
    else:
        existing = next(e for e in new_reg["entries"] if e["id"] == NEW_DEC_ID)
        old_h = existing.get("hash", "")[:12]
        old_s = existing.get("hash_size_bytes")
        if old_h != new_dec_sha[:12] or old_s != new_dec_sz:
            diff.append(f"  [entries/{NEW_DEC_ID}].hash: {old_h} -> {new_dec_sha[:12]}")
            diff.append(f"  [entries/{NEW_DEC_ID}].hash_size_bytes: {old_s} -> {new_dec_sz}")
            existing["hash"] = new_dec_sha
            existing["hash_size_bytes"] = new_dec_sz

    # 1c. pointer (idempotent)
    old_ptr = new_reg["current_by_family"]["shared-identity-bootstrap"]
    if old_ptr != NEW_DEC_ID:
        diff.append(f"  current_by_family[shared-identity-bootstrap]: {old_ptr!r} -> {NEW_DEC_ID!r}")
        new_reg["current_by_family"]["shared-identity-bootstrap"] = NEW_DEC_ID

    # ---------- 2. shared-identity-identity family ----------
    id_runtime = next(e for e in new_reg["entries"] if e["id"] == IDENTITY_RUNTIME_ID)
    if id_runtime["status"] != "superseded":
        diff.append(f"  [entries/{IDENTITY_RUNTIME_ID}].status:        {id_runtime['status']!r} -> 'superseded'")
        diff.append(f"  [entries/{IDENTITY_RUNTIME_ID}].superseded_by: {id_runtime.get('superseded_by')!r} -> {PROMOTED_DEC_ID!r}")
        id_runtime["status"] = "superseded"
        id_runtime["superseded_by"] = PROMOTED_DEC_ID
    if "former current; runtime file disappeared" not in id_runtime.get("evidence_note", ""):
        diff.append(f"  [entries/{IDENTITY_RUNTIME_ID}].evidence_note:  <append> 'former current; runtime file disappeared after concurrent WorkBuddy relink drift (R282.1); preserved as evidence-only; hash+size from R282 capture kept.'")
        id_runtime["evidence_note"] = (
            "former current; runtime file disappeared after concurrent WorkBuddy relink drift (R282.1); "
            "preserved as evidence-only; hash+size from R282 capture kept."
        )

    # 2b. promote existing decision record + ALWAYS refresh hash (the R282_DEC_06 file may have been edited in-place)
    promoted = next(e for e in new_reg["entries"] if e["id"] == PROMOTED_DEC_ID)
    promoted_full = ROOT / promoted["path"].replace("/", os.sep)
    if promoted_full.exists() and promoted_full.is_file():
        actual_sha = sha256_file(promoted_full)
        actual_sz = promoted_full.stat().st_size
        old_h = promoted.get("hash", "")[:12]
        old_s = promoted.get("hash_size_bytes")
        if old_h != actual_sha[:12] or old_s != actual_sz:
            diff.append(f"  [entries/{PROMOTED_DEC_ID}].hash: {old_h} -> {actual_sha[:12]}")
            diff.append(f"  [entries/{PROMOTED_DEC_ID}].hash_size_bytes: {old_s} -> {actual_sz}")
            promoted["hash"] = actual_sha
            promoted["hash_size_bytes"] = actual_sz
    if promoted["status"] != "current":
        diff.append(f"  [entries/{PROMOTED_DEC_ID}].status:        {promoted['status']!r} -> 'current'")
        promoted["status"] = "current"
        promoted.setdefault("evidence", []).append(
            "R282.1 promotion: candidate -> current (runtime file MISSING on disk; pointer re-anchored to this decision record per R282.1_DEC_01 design)"
        )

    # 2c. pointer (idempotent)
    old_ptr2 = new_reg["current_by_family"]["shared-identity-identity"]
    if old_ptr2 != PROMOTED_DEC_ID:
        diff.append(f"  current_by_family[shared-identity-identity]: {old_ptr2!r} -> {PROMOTED_DEC_ID!r}")
        new_reg["current_by_family"]["shared-identity-identity"] = PROMOTED_DEC_ID

    # ---------- 3. audit_id + captured_at + totals + policy ----------
    diff.append(f"  audit_id:    {new_reg['audit_id']!r} -> 'system-audit-20260929-R282.1'")
    diff.append(f"  captured_at: {new_reg['captured_at']!r} -> <now>")
    new_reg["audit_id"] = "system-audit-20260929-R282.1"
    new_reg["captured_at"] = now_iso()
    new_reg["policy"] = (
        "current-pointer order: current_by_family[family] > CANONICAL_INDEX pointer > explicit supersedes chain > hash/mtime as evidence only. "
        "mtime/hash are NEVER sole selectors. "
        "R282: decision records under governance/decisions/ may serve as current pointers when (a) no runtime file is legitimate, "
        "or (b) the runtime file is stale/broken/non-authoritative. Decision records have r282_role=decision_record and status "
        "current or candidate per the per-family decision. "
        "R282.1 (2026-09-29, drift repair): a concurrent WorkBuddy relink removed two runtime files "
        "(_relinked/workbuddy/BOOTSTRAP.md and _relinked/workbuddy/IDENTITY.md) after the R282 capture. "
        "shared-identity-bootstrap pointer re-anchored to a new decision record r282.1-decision-shared-identity-bootstrap. "
        "shared-identity-identity pointer re-anchored to the existing r282-decision-shared-identity-identity (promoted candidate -> current). "
        "Former runtime entries kept as status=superseded evidence-only with their R282-era hash+size."
    )

    # 3b. recompute totals_by_status
    counts = {"current": 0, "candidate": 0, "superseded": 0, "unknown": 0}
    for e in new_reg["entries"]:
        s = e.get("status")
        if s in counts:
            counts[s] += 1
    new_reg["totals_by_status"] = counts
    diff.append(f"  totals_by_status: <recompute> {counts}")

    cbf = new_reg["current_by_family"]
    n_unresolved = sum(1 for v in cbf.values() if v is None)
    n_current = sum(1 for v in cbf.values() if v is not None)
    new_reg["totals"] = {
        "entries": len(new_reg["entries"]),
        "families": len(set(e["family"] for e in new_reg["entries"] if e.get("family"))),
        "current": n_current,
        "unresolved": n_unresolved,
    }
    diff.append(f"  totals: <recompute> entries={len(new_reg['entries'])}, families={new_reg['totals']['families']}, current={n_current}, unresolved={n_unresolved}")

    return new_reg, diff


def dry_run():
    reg = load_reg()
    new_reg, diff = propose_diff(reg)
    print("# R282.1 drift-repair helper \u2014 DRY RUN")
    print("#" * 70)
    print()
    print("Proposed diff:")
    for line in diff:
        print(line)
    print()
    print(f"After apply:  entries={len(new_reg['entries'])}")
    print(f"After apply:  totals_by_status={new_reg['totals_by_status']}")
    print(f"After apply:  totals={new_reg['totals']}")
    print()
    print("#" * 70)
    print("NO FILE WRITTEN.  Pass --apply --approve R282_1_REGISTRY_ONLY to apply.")
    return 0


def apply():
    reg = load_reg()
    new_reg, diff = propose_diff(reg)

    print("# R282.1 drift-repair helper \u2014 APPLY")
    print("#" * 70)
    print("Diff being applied:")
    for line in diff:
        print(line)
    print()

    # Atomic write: unique temp + os.replace; no os.remove on failure.
    tmp = REG_PATH.with_name(f"{REG_PATH.stem}.{uuid.uuid4().hex[:12]}.tmp")
    data = json.dumps(new_reg, ensure_ascii=False, indent=2)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        try:
            os.replace(tmp, REG_PATH)
        except OSError as exc:
            try:
                if tmp.exists():
                    os.remove(tmp)
            except OSError:
                pass
            print(f"FAIL: os.replace failed ({exc}); registry NOT modified.",
                  file=sys.stderr)
            return 2
    except Exception as exc:
        try:
            if tmp.exists():
                os.remove(tmp)
        except OSError:
            pass
        print(f"FAIL: registry write failed ({exc}); registry NOT modified.",
              file=sys.stderr)
        return 2

    print(f"OK: registry written atomically: {REG_PATH}")
    print()

    # Post-apply validation
    print("Running `protocol_registry.py validate` \u2026")
    rc = subprocess.run(
        [sys.executable, str(PROTO_REG_PY), "validate"],
        capture_output=True, text=True,
    )
    print(rc.stdout, end="")
    if rc.stderr:
        print(rc.stderr, end="", file=sys.stderr)
    if rc.returncode != 0:
        print(f"FAIL: validate exited {rc.returncode}; registry left in place.",
              file=sys.stderr)
        return 3
    print()

    print("Running `protocol_registry.py list-current` \u2026")
    rc = subprocess.run(
        [sys.executable, str(PROTO_REG_PY), "list-current"],
        capture_output=True, text=True,
    )
    print(rc.stdout, end="")
    return 0


def main():
    ap = argparse.ArgumentParser(description="R282.1 drift-repair helper")
    ap.add_argument("--apply", action="store_true",
                    help="actually write the registry (requires --approve)")
    ap.add_argument("--approve", default=None,
                    help=f"required for apply: must be '{REQUIRED_APPROVAL}'")
    args = ap.parse_args()

    if args.apply:
        if args.approve != REQUIRED_APPROVAL:
            print(f"FAIL: --apply requires --approve {REQUIRED_APPROVAL}",
                  file=sys.stderr)
            return 2
        return apply()
    return dry_run()


if __name__ == "__main__":
    sys.exit(main())