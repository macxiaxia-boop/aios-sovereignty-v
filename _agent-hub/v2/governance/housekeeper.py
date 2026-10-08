#!/usr/bin/env python3
# housekeeper.py — file governance dry-run / audit.
#
# This tool is **dry-run by default**. It NEVER deletes, moves, or renames files.
# Apply mode (`--apply`) requires explicit flags AND a separate user approval gate.
#
# Functions in dry-run mode:
#   - placement violations (files at legacy roots that should live elsewhere)
#   - duplicate hash candidates (groups with sha256 identical content)
#   - bak / disabled suffix candidates
#   - storage threshold warnings
#   - rotation candidates for *.log files
#
# Output: writes JSON to stdout OR to file with --out.

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("D:/AIOS").resolve()
GOV = Path("D:/AIOS/_agent-hub/v2/governance")
RPT = Path("D:/AIOS/_agent-hub/v2/reports/system-audit-20260929")

PROTECTED_TOP = {
    ".git",
    "_agent-hub",
    "aios_tools",  # symlink to operator
    "aios_venv",  # symlink to operator
}

LEGACY_ZONES = {
    "aios_tasks", "daemons_v2", "_scripts", "_scripts_tmp", "_tools",
    "_out", "_patches", "_archived_2026-09-18", "_archived_20260925_P0",
    "_archived_20260925_R259_popup_cure_rebuild",
    "_dr_v3.0_uncompressed_workspace", "_e_drive_dedup_workspace",
    "_backups", "_backup_aios_exe_周二022609_093048", "_backup_aios_exe_周二022609_093503",
    "_r274_install_backup",
    "wmic_forensics", "_capability", "_workzone",
}

CANONICAL_TOP = {
    "agents", "protocols", "projects", "artifacts", "logs", "runs",
    "reports", "archive", "quarantine", "governance",
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%M:%S.%fZ")


def load_inventory(csv_path: Path):
    rows = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def safe_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def scan_placement_violations(rows):
    """Files newer than 7 days in clearly temporary zones (true violations only).

    LEGACY_ZONES as a whole are NOT violations — they remain valid homes for
    files already there. We only flag top-levels that are explicitly temporary:
      _backups/, _dr_v3.0_uncompressed_workspace/, _e_drive_dedup_workspace/,
      _r274_install_backup/, _archived_*/
    New work in those zones should NOT happen.
    """
    temp_zones = {
        "_backups", "_dr_v3.0_uncompressed_workspace",
        "_e_drive_dedup_workspace", "_r274_install_backup",
        "_archived_2026-09-18", "_archived_20260925_P0",
        "_archived_20260925_R259_popup_cure_rebuild",
    }
    out = []
    cutoff = datetime(2026, 9, 22, tzinfo=timezone.utc)
    for r in rows:
        if r["kind"] != "file":
            continue
        top = r["top_rel"]
        if top not in temp_zones:
            continue
        try:
            mt = datetime.fromisoformat(r["mtime_iso"].replace("Z", "+00:00"))
        except Exception:
            continue
        if mt >= cutoff:
            out.append({
                "path": r["rel_path"],
                "top": top,
                "size_bytes": safe_int(r["size_bytes"]),
                "mtime": r["mtime_iso"],
                "recommendation": f"consider moving to archive/ (top is temporary zone)",
            })
    # keep only newest 100 violations across zones
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out[:100]


def scan_duplicates(rows):
    """Files with identical sha256 (excluding zero-hash, missing hash)."""
    by_hash = defaultdict(list)
    for r in rows:
        if r["kind"] != "file":
            continue
        h = r.get("sha256", "") or ""
        if not h or h == "0" * 64:
            continue
        if r["hashed"] != "1":
            continue
        by_hash[h].append(r)
    groups = []
    for h, rs in by_hash.items():
        if len(rs) < 2:
            continue
        rs_sorted = sorted(rs, key=lambda x: x["mtime_iso"], reverse=True)
        canonical = rs_sorted[0]
        dups = rs_sorted[1:]
        groups.append({
            "sha256": h,
            "size_bytes": safe_int(canonical["size_bytes"]),
            "canonical": canonical["rel_path"],
            "duplicates": [d["rel_path"] for d in dups],
            "waste_bytes_if_kept_one": safe_int(canonical["size_bytes"]) * (len(rs) - 1),
        })
    groups.sort(key=lambda g: -g["waste_bytes_if_kept_one"])
    return groups


def scan_bak_disabled(rows):
    out = []
    for r in rows:
        if r["kind"] != "file":
            continue
        n = r["name"].lower()
        if any(n.endswith(s) for s in [".bak", ".disabled", ".disabled_real", ".disabled",
                                       ".DISABLED", ".bak_pre_v2", ".bak_v2_failed"]) or ".bak." in n:
            out.append({
                "path": r["rel_path"],
                "size_bytes": safe_int(r["size_bytes"]),
                "mtime": r["mtime_iso"],
                "category": "bak_or_disabled",
            })
    return out


def scan_storage_thresholds(rows):
    """Per-top total bytes vs thresholds from RETENTION_POLICY.md."""
    THRESHOLDS = {
        "_workzone": 600 * 1024 * 1024,
        "_capability": 200 * 1024 * 1024,
        "_backups": 100 * 1024 * 1024,
        "daemons_v2": 200 * 1024 * 1024,
    }
    by_top = Counter()
    for r in rows:
        if r["kind"] == "file":
            by_top[r["top_rel"]] += safe_int(r["size_bytes"])
    out = []
    for top, thr in THRESHOLDS.items():
        b = by_top.get(top, 0)
        if b >= thr:
            out.append({
                "top": top,
                "bytes": b,
                "threshold_bytes": thr,
                "status": "exceeds_threshold",
            })
    return out


def scan_log_rotation(rows):
    out = []
    for r in rows:
        if r["kind"] != "file":
            continue
        if not r["name"].endswith(".log"):
            continue
        # protect agent-owned
        if "_relinked" in r["rel_path"]:
            continue
        size = safe_int(r["size_bytes"])
        if size > 50 * 1024 * 1024:
            out.append({
                "path": r["rel_path"],
                "size_bytes": size,
                "recommendation": "rotate (rename .log -> .log.1)",
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", default=str(RPT / "FILE_INVENTORY.csv"))
    ap.add_argument("--out", default=str(GOV / "HOUSEKEEPER_REPORT.json"))
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", dest="dry_run", action="store_true",
                     default=True,
                     help="default mode: scan and report, never modify")
    grp.add_argument("--apply", dest="dry_run", action="store_false",
                     help="FORBIDDEN in this round; always exit 2")
    args = ap.parse_args()

    if not args.dry_run:
        print("ERROR: --apply is disabled in this round (R281.1 §7).", file=sys.stderr)
        print("See governance/RETENTION_POLICY.md §5 for the approval workflow.",
              file=sys.stderr)
        sys.exit(2)

    inv = Path(args.inventory)
    if not inv.exists():
        print(f"inventory not found: {inv}", file=sys.stderr)
        sys.exit(2)
    rows = load_inventory(inv)

    report = {
        "schema": 1,
        "captured_at": now_iso(),
        "root": str(ROOT),
        "inventory": str(inv),
        "mode": "dry-run",
        "totals": {"rows": len(rows)},
        "placement_violations": scan_placement_violations(rows),
        "duplicate_groups": scan_duplicates(rows)[:200],
        "bak_disabled": scan_bak_disabled(rows),
        "storage_threshold_breaches": scan_storage_thresholds(rows),
        "log_rotation_candidates": scan_log_rotation(rows),
    }

    # counts
    report["counts"] = {
        "placement_violations": len(report["placement_violations"]),
        "duplicate_groups": len(report["duplicate_groups"]),
        "bak_disabled": len(report["bak_disabled"]),
        "storage_threshold_breaches": len(report["storage_threshold_breaches"]),
        "log_rotation_candidates": len(report["log_rotation_candidates"]),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: unique temp → replace. Do NOT os.remove(target) on failure;
    # clean up only our own temp file. Target stays untouched.
    tmp = out.with_name(f"{out.stem}.{uuid.uuid4().hex[:12]}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, out)
    except OSError as exc:
        try:
            if tmp.exists():
                os.remove(tmp)
        except OSError:
            pass
        print(f"FAIL: write failed ({exc}); target {out} NOT modified.",
              file=sys.stderr)
        sys.exit(2)

    print(json.dumps({
        "ok": True,
        "mode": "dry-run",
        "out": str(out),
        "counts": report["counts"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
