#!/usr/bin/env python3
# protocol_registry.py — single-source-of-truth validator + publisher for
# D:\AIOS\_agent-hub\v2\governance\PROTOCOL_REGISTRY.json
#
# Subcommands:
#   validate          Check JSON schema, per-family current uniqueness,
#                     pointer integrity, current paths exist, ≤20MB file
#                     sha256 matches registry. exit non-zero on failure.
#   list-current      Print one line per family: family → current entry id
#                     OR UNRESOLVED.
#   publish           Default dry-run. Marks the previous current for a
#                     family as superseded, registers the new file as
#                     current, updates current_by_family pointer. NEVER
#                     moves/deletes/renames user files.
#
# SAFETY:
#   - publish only writes to the registry JSON file (atomic temp + replace).
#   - apply mode requires BOTH --apply AND --approve REGISTRY_ONLY flags.
#   - --registry can point at any JSON file (used for test isolation).
#   - apply NEVER deletes a target on replace failure — it errors out.

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("D:/AIOS").resolve()
DEFAULT_REGISTRY = Path("D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json").resolve()
# Test-isolated registry. Lives under governance/tests/fixtures/ and is
# NEVER a source of truth. R281.2: only PROTOCOL_REGISTRY.json at the
# governance/ root is canonical; tests/fixtures/ is excluded from current
# parsing by placement rule §5.
TEST_REGISTRY = Path("D:/AIOS/_agent-hub/v2/governance/tests/fixtures/TEST_ONLY_protocol_registry.json").resolve()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Schema ---------------------------------------------------------------- #

REQUIRED_TOP_FIELDS = {"schema", "audit_id", "captured_at", "policy",
                       "current_by_family", "entries"}
REQUIRED_ENTRY_FIELDS = {"id", "title", "path", "version", "status",
                         "family"}

ALLOWED_STATUS = {"current", "superseded", "candidate", "unknown"}


def sha256_file(path: Path, *, cap: int = 20 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    total = 0
    with open(path, "rb") as f:
        while True:
            buf = f.read(65536)
            if not buf:
                break
            h.update(buf)
            total += len(buf)
            if total >= cap:
                break
    return h.hexdigest()


def load_registry(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- validate -------------------------------------------------------------- #

def cmd_validate(args):
    reg_path = Path(args.registry)
    if not reg_path.exists():
        print(f"FAIL: registry not found: {reg_path}", file=sys.stderr)
        return 2
    try:
        reg = load_registry(reg_path)
    except Exception as e:
        print(f"FAIL: cannot parse registry JSON: {e}", file=sys.stderr)
        return 2

    failures = []

    # Top-level fields
    missing = REQUIRED_TOP_FIELDS - set(reg.keys())
    if missing:
        failures.append(f"top-level missing fields: {sorted(missing)}")

    # current_by_family structure
    cbf = reg.get("current_by_family", {})
    if not isinstance(cbf, dict):
        failures.append("current_by_family must be an object")

    entries = reg.get("entries", [])
    if not isinstance(entries, list):
        failures.append("entries must be an array")
        entries = []

    by_id = {}
    by_family = defaultdict(list)
    for e in entries:
        eid = e.get("id")
        if not eid:
            failures.append("entry missing id")
            continue
        if eid in by_id:
            failures.append(f"duplicate entry id: {eid}")
        by_id[eid] = e
        fam = e.get("family")
        if not fam:
            failures.append(f"entry {eid} missing family")
        else:
            by_family[fam].append(eid)
        # required fields
        miss = REQUIRED_ENTRY_FIELDS - set(e.keys())
        if miss:
            failures.append(f"entry {eid} missing fields: {sorted(miss)}")
        # status
        st = e.get("status")
        if st not in ALLOWED_STATUS:
            failures.append(f"entry {eid} status={st!r} not in {sorted(ALLOWED_STATUS)}")

    # Per-family: at most one current
    for fam, ids in by_family.items():
        currents = [i for i in ids if by_id[i].get("status") == "current"]
        if len(currents) > 1:
            failures.append(f"family {fam!r} has >1 current entries: {currents}")

    # current_by_family integrity
    for fam, pointer in cbf.items():
        if pointer is None:
            continue
        if pointer not in by_id:
            failures.append(f"current_by_family[{fam!r}] -> {pointer!r} not in entries")
            continue
        e = by_id[pointer]
        if e.get("family") != fam:
            failures.append(f"current_by_family[{fam!r}] -> {pointer!r} has family {e.get('family')!r}")
        if e.get("status") != "current":
            failures.append(f"current_by_family[{fam!r}] -> {pointer!r} status={e.get('status')!r} (must be current)")

    # Current paths must exist
    for e in entries:
        if e.get("status") != "current":
            continue
        p = e.get("path")
        if not p:
            failures.append(f"current {e['id']} path is null/empty")
            continue
        ap = ROOT / p.replace("/", os.sep)
        if not ap.exists():
            failures.append(f"current {e['id']} path missing on disk: {p}")

    # ≤20MB file hash check
    if not args.skip_hash_check:
        for e in entries:
            p = e.get("path")
            if not p:
                continue
            ap = ROOT / p.replace("/", os.sep)
            if not ap.exists() or not ap.is_file():
                continue
            sz = ap.stat().st_size
            if sz <= 0 or sz > 20 * 1024 * 1024:
                continue
            try:
                actual = sha256_file(ap)
            except OSError as exc:
                failures.append(f"{e['id']}: hash error: {exc}")
                continue
            recorded = e.get("hash")
            if recorded and recorded != actual:
                failures.append(f"{e['id']}: hash mismatch recorded={recorded[:12]} actual={actual[:12]}")

    # report
    if failures:
        print(f"FAIL ({len(failures)} issues):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("PASS: registry valid")
    print(f"  entries: {len(entries)}")
    print(f"  families: {len(by_family)}")
    print(f"  current_by_family pointers: {sum(1 for v in cbf.values() if v is not None)} "
          f"/ {len(cbf)} (rest unresolved)")
    return 0


# --- list-current ---------------------------------------------------------- #

def cmd_list_current(args):
    reg_path = Path(args.registry)
    if not reg_path.exists():
        print(f"FAIL: registry not found: {reg_path}", file=sys.stderr)
        return 2
    reg = load_registry(reg_path)
    cbf = reg.get("current_by_family", {})
    families = sorted(set([e["family"] for e in reg.get("entries", []) if e.get("family")]))
    print(f"# {reg_path.name} — current_by_family")
    print()
    for fam in families:
        pointer = cbf.get(fam)
        if pointer is None:
            print(f"  {fam:30s}  UNRESOLVED")
            continue
        e = next((x for x in reg.get("entries", []) if x.get("id") == pointer), None)
        if not e:
            print(f"  {fam:30s}  POINTER_BROKEN -> {pointer}")
            continue
        path = e.get("path") or "(no path)"
        print(f"  {fam:30s}  {pointer:35s}  {path}")
    return 0


# --- publish --------------------------------------------------------------- #

def cmd_publish(args):
    if not args.apply or args.approve != "REGISTRY_ONLY":
        print("DRY-RUN (default): would publish "
              f"family={args.family} id={args.id} path={args.path} "
              f"version={args.version} supersedes={args.supersedes or []}")
        print("  No file written. Pass --apply --approve REGISTRY_ONLY to actually apply.")
        # Still show the diff for review
        reg_path = Path(args.registry)
        if reg_path.exists():
            reg = load_registry(reg_path)
            current = next((e for e in reg.get("entries", [])
                           if e.get("family") == args.family and e.get("status") == "current"), None)
            if current:
                print(f"  [would-mark-superseded] current={current['id']}")
        return 0

    # Apply path
    reg_path = Path(args.registry)
    if not reg_path.exists():
        print(f"FAIL: registry not found: {reg_path}", file=sys.stderr)
        return 2
    reg = load_registry(reg_path)

    # Ensure family is present in current_by_family
    cbf = reg.setdefault("current_by_family", {})
    if args.family not in cbf:
        cbf[args.family] = None  # ambiguous → null until publish

    previous_current_id = cbf.get(args.family)
    new_entry = {
        "id": args.id,
        "title": args.title or args.id,
        "path": args.path,
        "version": args.version,
        "status": "current",
        "family": args.family,
        "supersedes": args.supersedes or [],
        "superseded_by": None,
        "evidence": [f"published via protocol_registry.py at {now_iso()}"],
    }
    if args.path and Path(args.path).exists():
        ap = ROOT / args.path.replace("/", os.sep) if not Path(args.path).is_absolute() else Path(args.path)
        if ap.exists() and ap.is_file() and 0 < ap.stat().st_size <= 20 * 1024 * 1024:
            try:
                new_entry["hash"] = sha256_file(ap)
            except OSError as exc:
                print(f"FAIL: hash error: {exc}", file=sys.stderr)
                return 2
    # Append entry
    reg.setdefault("entries", []).append(new_entry)
    # Mark previous current as superseded
    for e in reg["entries"]:
        if (e.get("family") == args.family
                and e.get("status") == "current"
                and e.get("id") != args.id):
            e["status"] = "superseded"
            e["superseded_by"] = args.id
    # Update pointer
    cbf[args.family] = args.id
    reg["captured_at"] = now_iso()

    # Atomic write: unique temp + replace. NO os.remove(target) on failure.
    tmp_path = reg_path.with_name(
        f"{reg_path.stem}.{uuid.uuid4().hex[:12]}.tmp"
    )
    data = json.dumps(reg, ensure_ascii=False, indent=2)
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        # Atomic replace; do NOT os.remove target on failure.
        try:
            os.replace(tmp_path, reg_path)
        except OSError as exc:
            # Cleanup our own temp only
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            print(f"FAIL: os.replace failed ({exc}); registry NOT modified. "
                  "Temp file cleaned. Target untouched.", file=sys.stderr)
            return 2
    except Exception as exc:
        try:
            if tmp_path.exists():
                os.remove(tmp_path)
        except OSError:
            pass
        print(f"FAIL: registry write failed ({exc}); registry NOT modified.",
              file=sys.stderr)
        return 2

    print(f"OK: published {args.id} (family={args.family})")
    if previous_current_id:
        print(f"  previous current {previous_current_id} marked superseded")
    print(f"  registry: {reg_path}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY),
                    help=f"path to registry JSON (default {DEFAULT_REGISTRY})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_v = sub.add_parser("validate", help="validate registry JSON")
    sp_v.add_argument("--skip-hash-check", action="store_true")

    sp_l = sub.add_parser("list-current", help="list current_by_family")

    sp_p = sub.add_parser("publish", help="publish a new current entry")
    sp_p.add_argument("--family", required=True)
    sp_p.add_argument("--id", required=True)
    sp_p.add_argument("--path", required=True)
    sp_p.add_argument("--version", required=True)
    sp_p.add_argument("--title", default=None)
    sp_p.add_argument("--supersedes", nargs="*", default=[])
    sp_p.add_argument("--apply", action="store_true",
                      help="actually modify the registry (requires --approve)")
    sp_p.add_argument("--approve", default=None,
                      help="required for apply: must be 'REGISTRY_ONLY'")

    args = ap.parse_args()
    if args.cmd == "validate":
        return cmd_validate(args)
    if args.cmd == "list-current":
        return cmd_list_current(args)
    if args.cmd == "publish":
        return cmd_publish(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
