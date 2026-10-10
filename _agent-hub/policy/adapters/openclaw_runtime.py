#!/usr/bin/env python3
# openclaw_runtime.py - EXT-D 2026-10-10 reads from adapters_registry
from __future__ import annotations
import os, sys
_POLICY_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _POLICY_DIR not in sys.path:
    sys.path.insert(0, _POLICY_DIR)
from adapters_registry import get_runtime_info, invalidate  # EXT-D shared

RUNTIME_HOST = "openclaw"

def healthz():
    return get_runtime_info(RUNTIME_HOST)

def validate(model, provider, *, request_id):
    """EXT-D-compatible validate. Returns (ok, reason)."""
    info = healthz()
    if provider != info["provider_default"]:
        return False, "provider_not_allowed"
    if model != info["model_default"]:
        return False, "model_not_allowed"
    return True, "ok"

if __name__ == "__main__":
    import json
    print(json.dumps(healthz(), indent=2, default=str))
