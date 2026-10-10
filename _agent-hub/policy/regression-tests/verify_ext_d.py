#!/usr/bin/env python3
# verify_ext_d.py - 4-adapter registry smoke test (EXT-D)
import sys, json
POLICY_DIR = r"D:\AIOS\_agent-hub\policy"
if POLICY_DIR not in sys.path:
    sys.path.insert(0, POLICY_DIR)
from adapters_registry import get_runtime_info, invalidate

results = []
for host in ["codex", "claude_code", "hermes", "openclaw"]:
    invalidate()
    info = get_runtime_info(host)
    results.append(info)
    assert info["provider_default"] == "MiniMax", f"{host} provider mismatch: {info}"
    assert info["model_default"] == "MiniMax-M3", f"{host} model mismatch: {info}"

print("4/4 adapters OK")
for r in results:
    print(json.dumps(r, default=str))
