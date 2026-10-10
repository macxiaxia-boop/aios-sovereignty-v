#!/usr/bin/env python3
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
