#!/usr/bin/env python3
"""Verify model-policy.v1.yaml sha256 against its manifest.
Used by register_reconciler.cmd before schtasks registration.
Returns 0 on match, 2 on mismatch, 3 on missing.
"""
import sys, hashlib, re
from pathlib import Path

POLICY = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml")
MANIFEST = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256")

def main():
    if not POLICY.exists():
        print(f"[FATAL] policy file missing: {POLICY}", file=sys.stderr)
        sys.exit(3)
    if not MANIFEST.exists():
        print(f"[FATAL] manifest missing: {MANIFEST}", file=sys.stderr)
        sys.exit(3)
    actual = hashlib.sha256(POLICY.read_bytes()).hexdigest().upper()
    expected = None
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line.startswith("sha256:"):
            expected = line.split(":", 1)[1].strip().upper()
            break
    if not expected:
        print(f"[FATAL] manifest format wrong (no 'sha256:' line)", file=sys.stderr)
        sys.exit(3)
    print(f"actual   = {actual}")
    print(f"expected = {expected}")
    if actual == expected:
        print("[OK] sha256 match")
        sys.exit(0)
    print("[FATAL] sha256 mismatch — refuse to proceed")
    sys.exit(2)

if __name__ == "__main__":
    main()