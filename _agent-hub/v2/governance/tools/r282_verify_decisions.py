#!/usr/bin/env python3
"""R282 final verification: hash + existence cross-check on decision-record entries."""
import hashlib
import json
from pathlib import Path

REG_PATH = Path("D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json")
ROOT = Path("D:/AIOS")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


with open(REG_PATH, "r", encoding="utf-8") as f:
    reg = json.load(f)

decisions = [e for e in reg["entries"] if e.get("r282_role") == "decision_record"]
print(f"decision_records_in_registry: {len(decisions)}")

mismatches = []
all_ok = True
for e in decisions:
    rel = e["path"]
    abs_p = ROOT / rel
    if not abs_p.exists():
        mismatches.append(("MISSING", e["id"], str(abs_p)))
        all_ok = False
        continue
    actual = sha256_file(abs_p)
    recorded = e.get("hash", "")
    size_actual = abs_p.stat().st_size
    size_recorded = e.get("hash_size_bytes", 0)
    if actual != recorded:
        mismatches.append(("HASH_MISMATCH", e["id"], actual[:12], recorded[:12]))
        all_ok = False
    if size_actual != size_recorded:
        mismatches.append(("SIZE_MISMATCH", e["id"], size_actual, size_recorded))
        all_ok = False

print(f"mismatches: {len(mismatches)}")
for m in mismatches:
    print(f"  {m}")

# Also verify: every current_by_family pointer resolves to an existing entry
print()
print("current_by_family resolution check:")
cbf = reg["current_by_family"]
by_id = {e["id"]: e for e in reg["entries"]}
pointer_problems = []
for fam, ptr in cbf.items():
    if ptr is None:
        pointer_problems.append(("NULL", fam))
        continue
    if ptr not in by_id:
        pointer_problems.append(("BROKEN", fam, ptr))
        continue
    e = by_id[ptr]
    if e.get("family") != fam:
        pointer_problems.append(("FAMILY_MISMATCH", fam, ptr, e.get("family")))
    if e.get("status") != "current":
        pointer_problems.append(("STATUS_NOT_CURRENT", fam, ptr, e.get("status")))
    p = ROOT / e["path"]
    if not p.exists():
        pointer_problems.append(("PATH_MISSING", fam, ptr, str(p)))

print(f"pointer_problems: {len(pointer_problems)}")
for p in pointer_problems:
    print(f"  {p}")

print()
print(f"OVERALL: {'PASS' if (all_ok and not pointer_problems) else 'FAIL'}")
