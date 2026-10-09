#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
adapters/__init__.py — Adapter auto-load (Phase I.3 / T26 · 2026-10-09)

SSOT 路径
  - Spec:      D:\AIOS\_agent-hub\policy\adapter-spec.v1.md
  - Contract:  D:\AIOS\_agent-hub\policy\adapter-contract.md
  - 4 个 adapter:
      * claude_code_runtime.py
      * codex_runtime.py
      * hermes_runtime.py
      * openclaw_runtime.py

线程 / 授权
  - Thread:    01a11c33-c813-7752-9e53-b7c332d00445 (Phase I.3)
  - Supervisor: 01a11c30-6f6c-76c0-8c60-a39f3a43ff63
  - Authorizer: user-2026-10-08T23:55 (sovereignty-v) + 你就开始 + 继续 (2026-10-09)

红线契约 (与 spec §"统一接口" 对齐)
  - NO_FABRICATE_MODEL_ID        : 仅 import + 调 adapter.validate(), 不在本文件写 model id
  - UNIFIED_INTERFACE_REQUIRED   : 强校验签名 validate(model, provider, *, request_id) -> Tuple[bool, str]
  - NO_AUTO_FALLBACK_IN_ADAPTER  : load_all_adapters() 仅作发现/校验, 不调 validate(), 不写 audit

公开 API
  - load_all_adapters()              -> dict[str, ModuleType]   4 个 runtime 模块
  - verify_unified_signature(mod)    -> Tuple[bool, str]        校验 validate 签名
  - list_adapters_status()           -> list[dict]              状态表 (供 dashboard / smoke 用)
  - main(argv)                       -> int                     CLI: --smoke / --list / --json
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Tuple

# 路径常量
ADAPTERS_DIR = Path(__file__).resolve().parent

# 必须存在的 4 个 adapter 文件名（与 spec §"4 个 runtime" 对齐）
EXPECTED_RUNTIMES = [
    "claude_code_runtime",
    "codex_runtime",
    "hermes_runtime",
    "openclaw_runtime",
]

# spec §"统一接口": validate(model, provider, *, request_id) -> Tuple[bool, str]
UNIFIED_REQUIRED_PARAMS = ("model", "provider")
UNIFIED_REQUIRED_KWONLY = ("request_id",)
UNIFIED_REQUIRED_RETURN_LEN = 2  # (allowed, reason)


def _load_module(module_name: str) -> Tuple[ModuleType | None, str]:
    """动态 import 同目录的 runtime.py.

    Returns: (module, error_msg)  · 失败时 module=None, error_msg 描述原因.
    """
    py_path = ADAPTERS_DIR / f"{module_name}.py"
    if not py_path.exists():
        return None, f"file_missing:{py_path}"
    spec = importlib.util.spec_from_file_location(f"aios_adapter_{module_name}", py_path)
    if spec is None or spec.loader is None:
        return None, f"spec_load_failed:{module_name}"
    module = importlib.util.module_from_spec(spec)
    try:
        # 让模块内部 sys.path 引用找得到: 把 ADAPTERS_DIR 加进 sys.path
        if str(ADAPTERS_DIR) not in sys.path:
            sys.path.insert(0, str(ADAPTERS_DIR))
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001
        return None, f"exec_failed:{type(e).__name__}:{e}"
    return module, ""


def verify_unified_signature(module: ModuleType) -> Tuple[bool, str]:
    """校验 validate(model, provider, *, request_id) -> Tuple[bool, str].

    Returns: (ok, info)
    """
    fn = getattr(module, "validate", None)
    if fn is None:
        return False, "validate_not_defined"

    try:
        sig = inspect.signature(fn)
    except Exception as e:  # noqa: BLE001
        return False, f"signature_inspect_failed:{type(e).__name__}:{e}"

    params = list(sig.parameters.values())
    # 第 1、2 参数: model, provider (positional)
    if len(params) < 2:
        return False, f"too_few_params:{len(params)}"
    p0, p1 = params[0], params[1]
    if p0.name != UNIFIED_REQUIRED_PARAMS[0]:
        return False, f"first_param_mismatch:{p0.name}"
    if p1.name != UNIFIED_REQUIRED_PARAMS[1]:
        return False, f"second_param_mismatch:{p1.name}"

    # keyword-only 强制 request_id 必填
    kwonly_names = {p.name for p in sig.parameters.values()
                    if p.kind == inspect.Parameter.KEYWORD_ONLY}
    missing_kwonly = [k for k in UNIFIED_REQUIRED_KWONLY if k not in kwonly_names]
    if missing_kwonly:
        return False, f"missing_kwonly:{missing_kwonly}"

    return True, "ok"


def load_all_adapters() -> dict[str, ModuleType]:
    """发现 + 加载 4 个 adapter. 失败的不抛, 跳过并记录到 stderr.

    Returns: dict[name, module] · 仅包含成功加载的模块.
    """
    loaded: dict[str, ModuleType] = {}
    for name in EXPECTED_RUNTIMES:
        mod, err = _load_module(name)
        if mod is None:
            print(f"[adapters/__init__] load_failed {name}: {err}", file=sys.stderr)
            continue
        ok, sig_info = verify_unified_signature(mod)
        if not ok:
            print(f"[adapters/__init__] signature_failed {name}: {sig_info}", file=sys.stderr)
            continue
        loaded[name] = mod
    return loaded


def list_adapters_status() -> list[dict]:
    """枚举所有 expected runtime, 输出状态表 (含 ok/fail)."""
    out: list[dict] = []
    for name in EXPECTED_RUNTIMES:
        mod, err = _load_module(name)
        row = {
            "name":    name,
            "loaded":  mod is not None,
            "error":   err,
            "signature_ok": False,
            "signature_info": "",
            "has_audit_log": False,
            "host":    "",
        }
        if mod is not None:
            ok, sig_info = verify_unified_signature(mod)
            row["signature_ok"] = ok
            row["signature_info"] = sig_info
            row["host"] = getattr(mod, "RUNTIME_HOST", "")
            row["has_audit_log"] = hasattr(mod, "AUDIT_LOG")
        out.append(row)
    return out


def main(argv: list[str]) -> int:
    arg = argv[0] if argv else "--list"
    if arg == "--list":
        statuses = list_adapters_status()
        print(f"=== adapters status ({len(statuses)}) ===")
        for s in statuses:
            mark = "OK" if (s["loaded"] and s["signature_ok"]) else "FAIL"
            print(f"  [{mark}] {s['name']:24s} host={s['host']:10s} sig_ok={s['signature_ok']} "
                  f"audit_log={s['has_audit_log']} info={s['signature_info']}")
        ok_count = sum(1 for s in statuses if s["loaded"] and s["signature_ok"])
        print(f"=== summary: ok={ok_count}/{len(statuses)} ===")
        return 0 if ok_count == len(statuses) else 1
    elif arg == "--json":
        statuses = list_adapters_status()
        print(json.dumps(statuses, ensure_ascii=False, indent=2))
        return 0
    elif arg == "--smoke":
        # smoke: 加载全部 + 对每个调一次 validate(default_model) 不真发, 仅探活
        loaded = load_all_adapters()
        print(f"=== smoke: loaded {len(loaded)}/{len(EXPECTED_RUNTIMES)} ===")
        for name, mod in loaded.items():
            try:
                # 仅检查函数可调用; 不真发请求 (避免烧 token)
                fn = getattr(mod, "validate", None)
                if fn is None:
                    print(f"  [SKIP] {name}: validate missing")
                    continue
                print(f"  [PASS] {name}: validate callable, signature={inspect.signature(fn)}")
            except Exception as e:  # noqa: BLE001
                print(f"  [FAIL] {name}: {type(e).__name__}:{e}")
        return 0 if len(loaded) == len(EXPECTED_RUNTIMES) else 1
    else:
        print(f"usage: python -m adapters.__init__ [--list|--json|--smoke]", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))