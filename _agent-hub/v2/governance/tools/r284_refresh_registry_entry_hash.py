"""R284 · update r284-fixed-cloudtech-xml entry hash + size fields
Mirrors R283's atomic metadata refresh pattern (temp + os.replace, no os.remove).
Updates ONLY the r284-fixed-cloudtech-xml entry's hash + hash_size_bytes.
"""
import json
import hashlib
import os
import sys
import uuid
from pathlib import Path

REG_PATH = Path(r"D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json")
ENTRY_ID = "r284-fixed-cloudtech-xml"

# Load registry
reg = json.loads(REG_PATH.read_text(encoding="utf-8"))

# Find the entry
target = None
for e in reg.get("entries", []):
    if e.get("id") == ENTRY_ID:
        target = e
        break

if target is None:
    print(f"FATAL: entry id={ENTRY_ID} not found")
    sys.exit(1)

# Resolve entry path relative to AIOS root
entry_path_str = target.get("path")
if not entry_path_str:
    print("FATAL: entry has no path")
    sys.exit(1)

file_path = Path("D:/AIOS") / entry_path_str
if not file_path.exists():
    print(f"FATAL: entry path does not exist: {file_path}")
    sys.exit(1)

# Compute actual hash + size
content = file_path.read_bytes()
actual_hash = hashlib.sha256(content).hexdigest()
actual_size = len(content)

# Capture pre-state
pre_hash = target.get("hash")
pre_size = target.get("hash_size_bytes")
print(f"Pre-update: hash={pre_hash} · size={pre_size}")

# Update ONLY hash + hash_size_bytes
target["hash"] = actual_hash
target["hash_size_bytes"] = actual_size

# Atomic write: temp + os.replace
tmp = REG_PATH.with_suffix(f".json.tmp_{uuid.uuid4().hex[:8]}")
try:
    tmp.write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, REG_PATH)
    print(f"Post-update: hash={actual_hash} · size={actual_size}")
    print(f"Atomic write OK · path={REG_PATH}")
except Exception as e:
    if tmp.exists():
        tmp.unlink()
    print(f"FATAL: atomic write failed: {e}")
    sys.exit(1)

# Verify round-trip
verify = json.loads(REG_PATH.read_text(encoding="utf-8"))
for e in verify["entries"]:
    if e.get("id") == ENTRY_ID:
        print(f"Verified: hash={e.get('hash')} · size={e.get('hash_size_bytes')}")
        break

print("OK · metadata refresh complete")