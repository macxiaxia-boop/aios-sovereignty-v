#!/usr/bin/env python3
"""run_all.py - Unified regression entry. Run all EXT-D/EXT-E checks."""
import subprocess, sys
from pathlib import Path

RT = Path(__file__).resolve().parent

TESTS = [
    ("verify_ext_d", RT / "verify_ext_d.py"),
    ("discover_cloudtech", RT / "discover_cloudtech.py"),
    ("yaml sha manifest", RT / "_yaml_sha_check.py"),
]

results = []
for name, path in TESTS:
    print("=== " + name + " ===")
    if not path.exists():
        print("  [SKIP] file not found")
        results.append((name, "SKIP"))
        continue
    r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, shell=False)
    if r.returncode == 0:
        print(r.stdout[:300])
        print("  [PASS]")
        results.append((name, "PASS"))
    else:
        print(r.stdout[:300])
        print("  [FAIL] exit=" + str(r.returncode))
        print(r.stderr[:300])
        results.append((name, "FAIL"))

print()
print("=== SUMMARY ===")
for n, s in results:
    print("  " + n + ": " + s)
fail = [n for n, s in results if s == "FAIL"]
if fail:
    print("FAILED:", fail)
    sys.exit(1)
print("ALL PASSED")
sys.exit(0)
