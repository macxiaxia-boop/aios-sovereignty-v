import os, shutil, hashlib, subprocess
import sys

RT = r"D:\AIOS\_agent-hub\policy\regression-tests"
os.makedirs(RT, exist_ok=True)

def w(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest().upper()
    print(f"wrote {os.path.basename(path):32s}  {os.path.getsize(path):6}B  sha256={h}")

# Copy verify_ext_d.py
src = r"D:\AIOS\_agent-hub\scripts\verify_ext_d.py"
dst = os.path.join(RT, "verify_ext_d.py")
shutil.copy2(src, dst)
print("copied verify_ext_d.py")

src = r"D:\AIOS\_agent-hub\scripts\discover_cloudtech.py"
dst = os.path.join(RT, "discover_cloudtech.py")
shutil.copy2(src, dst)
print("copied discover_cloudtech.py")

# _yaml_sha_check.py
yamlsha = '''#!/usr/bin/env python3
import sys, os, hashlib
hub_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
yaml_p = os.path.join(hub_root, "policy", "model-policy.v1.yaml")
sha_p = os.path.join(hub_root, "policy", "model-policy.v1.sha256")
if not os.path.exists(yaml_p) or not os.path.exists(sha_p):
    print("yaml or sha missing", file=sys.stderr); sys.exit(1)
actual = hashlib.sha256(open(yaml_p, "rb").read()).hexdigest().upper()
expected = None
for line in open(sha_p, encoding="utf-8"):
    if line.startswith("sha256:"):
        expected = line.split(":", 1)[1].strip().upper()
        break
if expected is None:
    print("no sha256 in manifest", file=sys.stderr); sys.exit(2)
if actual != expected:
    print(f"MISMATCH yaml={actual[:16]}.. manifest={expected[:16]}..", file=sys.stderr); sys.exit(3)
print("yaml sha matches manifest")
'''
w(os.path.join(RT, "_yaml_sha_check.py"), yamlsha)

# test_adapter_registry.py
runner = '''#!/usr/bin/env python3
"""test_adapter_registry.py - pytest wrapper for EXT-D regression."""
import os, subprocess, sys
import pytest


def test_verify_ext_d_passes():
    rt_root = os.path.dirname(os.path.abspath(__file__))
    hub_root = os.path.normpath(os.path.join(rt_root, "..", ".."))
    verify = os.path.join(hub_root, "scripts", "verify_ext_d.py")
    if not os.path.exists(verify):
        verify = os.path.join(rt_root, "verify_ext_d.py")
    r = subprocess.run([sys.executable, verify], capture_output=True, text=True, shell=False)
    assert r.returncode == 0, "verify_ext_d.py failed: " + r.stderr
    assert "4/4 adapters OK" in r.stdout, "missing 4/4: " + r.stdout


def test_discover_cloudtech_runs():
    rt_root = os.path.dirname(os.path.abspath(__file__))
    hub_root = os.path.normpath(os.path.join(rt_root, "..", ".."))
    discover = os.path.join(hub_root, "scripts", "discover_cloudtech.py")
    if not os.path.exists(discover):
        discover = os.path.join(rt_root, "discover_cloudtech.py")
    r = subprocess.run([sys.executable, discover], capture_output=True, text=True, shell=False)
    assert r.returncode == 0, "discover failed: " + r.stderr
    import json as _json
    out = _json.loads(r.stdout)
    assert out["count"] >= 1, "no CloudTech: " + r.stdout


def test_yaml_sha_matches_manifest():
    import hashlib
    rt_root = os.path.dirname(os.path.abspath(__file__))
    hub_root = os.path.normpath(os.path.join(rt_root, "..", ".."))
    yaml_p = os.path.join(hub_root, "policy", "model-policy.v1.yaml")
    sha_p = os.path.join(hub_root, "policy", "model-policy.v1.sha256")
    if not os.path.exists(yaml_p) or not os.path.exists(sha_p):
        pytest.skip("yaml/sha missing")
    actual = hashlib.sha256(open(yaml_p, "rb").read()).hexdigest().upper()
    expected = None
    for line in open(sha_p, encoding="utf-8"):
        if line.startswith("sha256:"):
            expected = line.split(":", 1)[1].strip().upper()
            break
    assert expected is not None, "no sha256 in manifest"
    assert actual == expected, f"mismatch yaml={actual[:16]}.. manifest={expected[:16]}.."
'''
w(os.path.join(RT, "test_adapter_registry.py"), runner)

# run_all.py
runall = '''#!/usr/bin/env python3
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
'''
w(os.path.join(RT, "run_all.py"), runall)

# Run pytest
print()
print("=== pytest regression-tests/test_*.py ===")
r = subprocess.run([sys.executable, "-m", "pytest", RT, "-v", "--tb=line"], capture_output=True, text=True, shell=False)
print(r.stdout[-2500:])
print("rc:", r.returncode)
print("stderr:", r.stderr[-500:])
