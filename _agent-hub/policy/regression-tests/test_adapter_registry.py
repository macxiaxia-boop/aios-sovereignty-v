#!/usr/bin/env python3
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
