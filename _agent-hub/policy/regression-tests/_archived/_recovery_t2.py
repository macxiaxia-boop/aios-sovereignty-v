import os, hashlib

POLICY_DIR = r"D:\AIOS\_agent-hub\policy"
ADAPTERS_DIR = os.path.join(POLICY_DIR, "adapters")
SCRIPTS_DIR = r"D:\AIOS\_agent-hub\scripts"
KNOWLEDGE_DIR = r"D:\AIOS\_agent-hub\knowledge"

os.makedirs(ADAPTERS_DIR, exist_ok=True)
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# =============== adapters_registry.py ===============
reg = """#!/usr/bin/env python3
# adapters_registry.py - EXT-D (R1345) 2026-10-10 recovery
# Singleton default-model registry shared by 4 adapters.
# Additive refactor of per-adapter POLICY_PATH + SHA_PATH + yaml.safe_load.
# Cache 30s. Fail-soft on missing/corrupt yaml.
from __future__ import annotations
import hashlib, time
from pathlib import Path

POLICY_PATH = Path(__file__).resolve().parent / "model-policy.v1.yaml"
SHA_PATH = Path(__file__).resolve().parent / "model-policy.v1.sha256"

_cache = None
_cache_ts = 0.0
_CACHE_TTL = 30.0


def _read_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _verify_sha256():
    if not POLICY_PATH.exists() or not SHA_PATH.exists():
        return False, "policy or manifest missing"
    actual = hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest().upper()
    lines = SHA_PATH.read_text(encoding="utf-8").splitlines()
    expected = None
    for line in lines:
        if line.startswith("sha256:"):
            expected = line.split(":", 1)[1].strip().upper()
            break
    if not expected:
        return False, "manifest format invalid"
    return actual == expected, ("match" if expected == actual else "MISMATCH")


def get_default_model():
    global _cache, _cache_ts
    now = time.time()
    if _cache is not None and (now - _cache_ts) < _CACHE_TTL:
        return _cache
    try:
        ok, _ = _verify_sha256()
        if not ok:
            _cache = (None, None, now)
            _cache_ts = now
            return _cache
        pol = _read_yaml(POLICY_PATH)
        mp = pol.get("model_policy", {}) if pol else {}
        _cache = (mp.get("default_provider"), mp.get("default_model"), now)
        _cache_ts = now
        return _cache
    except Exception:
        _cache = (None, None, now)
        _cache_ts = now
        return _cache


def invalidate():
    global _cache, _cache_ts
    _cache = None
    _cache_ts = 0.0


def get_runtime_info(runtime_host):
    provider, model, ts = get_default_model()
    return {
        "runtime_host": runtime_host,
        "provider_default": provider,
        "model_default": model,
        "ts": ts,
    }
"""

# =============== 4 adapter runtimes (all read from registry) ===============
def runtime_for(host):
    return (
        "#!/usr/bin/env python3" + chr(10)
        + "# " + host + "_runtime.py - EXT-D 2026-10-10 reads from adapters_registry" + chr(10)
        + "from __future__ import annotations" + chr(10)
        + "import os, sys" + chr(10)
        + "_POLICY_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), \"..\"))" + chr(10)
        + "if _POLICY_DIR not in sys.path:" + chr(10)
        + "    sys.path.insert(0, _POLICY_DIR)" + chr(10)
        + "from adapters_registry import get_runtime_info, invalidate  # EXT-D shared" + chr(10)
        + chr(10)
        + "RUNTIME_HOST = \"" + host + "\"" + chr(10)
        + chr(10)
        + "def healthz():" + chr(10)
        + "    return get_runtime_info(RUNTIME_HOST)" + chr(10)
        + chr(10)
        + "def validate(model, provider, *, request_id):" + chr(10)
        + "    \"\"\"EXT-D-compatible validate. Returns (ok, reason).\"\"\"" + chr(10)
        + "    info = healthz()" + chr(10)
        + "    if provider != info[\"provider_default\"]:" + chr(10)
        + "        return False, \"provider_not_allowed\"" + chr(10)
        + "    if model != info[\"model_default\"]:" + chr(10)
        + "        return False, \"model_not_allowed\"" + chr(10)
        + "    return True, \"ok\"" + chr(10)
        + chr(10)
        + "if __name__ == \"__main__\":" + chr(10)
        + "    import json" + chr(10)
        + "    print(json.dumps(healthz(), indent=2, default=str))" + chr(10)
    )


# =============== scripts/verify_ext_d.py ===============
verify = (
    "#!/usr/bin/env python3" + chr(10)
    + "# verify_ext_d.py - 4-adapter registry smoke test (EXT-D)" + chr(10)
    + "import sys, json" + chr(10)
    + "POLICY_DIR = r\"D:\\AIOS\\_agent-hub\\policy\"" + chr(10)
    + "if POLICY_DIR not in sys.path:" + chr(10)
    + "    sys.path.insert(0, POLICY_DIR)" + chr(10)
    + "from adapters_registry import get_runtime_info, invalidate" + chr(10)
    + chr(10)
    + "results = []" + chr(10)
    + "for host in [\"codex\", \"claude_code\", \"hermes\", \"openclaw\"]:" + chr(10)
    + "    invalidate()" + chr(10)
    + "    info = get_runtime_info(host)" + chr(10)
    + "    results.append(info)" + chr(10)
    + "    assert info[\"provider_default\"] == \"MiniMax\", f\"{host} provider mismatch: {info}\"" + chr(10)
    + "    assert info[\"model_default\"] == \"MiniMax-M3\", f\"{host} model mismatch: {info}\"" + chr(10)
    + chr(10)
    + "print(\"4/4 adapters OK\")" + chr(10)
    + "for r in results:" + chr(10)
    + "    print(json.dumps(r, default=str))" + chr(10)
)


# =============== scripts/discover_cloudtech.py ===============
discover = """#!/usr/bin/env python3
# discover_cloudtech.py - EXT-E (R1346) 2026-10-10 recovery
# Dynamic discovery of CloudTech installation paths.
# Reads common prefixes (D:/C:/ + CloudTech-Portable / CloudTech / cloudtech-saas)
# and emits structured JSON to stdout for EX-rule integration.
from __future__ import annotations
import json, os
from pathlib import Path

CANDIDATE_ROOTS = [
    ("D:", "CloudTech-Portable"),
    ("D:", "CloudTech"),
    ("D:", "cloudtech"),
    ("D:", "CloudTech-Pro"),
    ("C:", "CloudTech-Portable"),
    ("C:", "CloudTech"),
    ("C:", "cloudtech"),
]
AIOS_CLOUDTECH_PARENTS = ["D:/AIOS", "D:/AIOS/kernel"]


def discover_paths():
    import time
    found = []
    timestamp = int(time.time())
    for drive, name in CANDIDATE_ROOTS:
        root = Path(f"{drive}/{name}")
        if root.is_dir():
            found.append({"prefix": str(root).replace("\\\\", "/"), "kind": "install_root", "source": "candidate_root"})
    for parent in AIOS_CLOUDTECH_PARENTS:
        p = Path(parent)
        if not p.is_dir():
            continue
        for entry in sorted(p.iterdir()):
            if entry.is_dir() and "cloudtech" in entry.name.lower():
                found.append({"prefix": str(entry).replace("\\\\", "/"), "kind": "internal_sibling", "source": "aios_child_scan"})
    uniq = {}
    for f in found:
        uniq.setdefault(f["prefix"], f)
    return {"generated_at": timestamp, "schema": "r1346-cloudtech-prefix-list-v1", "count": len(uniq), "prefixes": list(uniq.values())}


if __name__ == "__main__":
    print(json.dumps(discover_paths(), indent=2, ensure_ascii=False))
"""

# Write all
files_written = {}
def w(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest().upper()
    files_written[path] = (len(content), h)
    print(f"wrote {os.path.basename(path):40s}  {len(content):6}B  sha256={h}")

w(os.path.join(POLICY_DIR, "adapters_registry.py"), reg)
w(os.path.join(ADAPTERS_DIR, "codex_runtime.py"), runtime_for("codex"))
w(os.path.join(ADAPTERS_DIR, "claude_code_runtime.py"), runtime_for("claude_code"))
w(os.path.join(ADAPTERS_DIR, "hermes_runtime.py"), runtime_for("hermes"))
w(os.path.join(ADAPTERS_DIR, "openclaw_runtime.py"), runtime_for("openclaw"))
w(os.path.join(SCRIPTS_DIR, "verify_ext_d.py"), verify)
w(os.path.join(SCRIPTS_DIR, "discover_cloudtech.py"), discover)

# Run discover_cloudtech to produce the JSON
import subprocess
r = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "discover_cloudtech.py")], capture_output=True, text=True, shell=False)
print()
print("discover_cloudtech output:")
print(r.stdout)
if r.returncode == 0 and r.stdout:
    cloudtech_json_path = os.path.join(KNOWLEDGE_DIR, "cloudtech_paths.json")
    with open(cloudtech_json_path, "w", encoding="utf-8") as f:
        f.write(r.stdout)
    h = hashlib.sha256(open(cloudtech_json_path, "rb").read()).hexdigest().upper()
    print(f"wrote cloudtech_paths.json  {os.path.getsize(cloudtech_json_path)}B  sha256={h}")

# Run verify_ext_d
print()
print("=== verify_ext_d.py ===")
r = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "verify_ext_d.py")], capture_output=True, text=True, shell=False)
print(r.stdout)
print("rc:", r.returncode)
if r.returncode != 0:
    print("stderr:", r.stderr)

import sys
