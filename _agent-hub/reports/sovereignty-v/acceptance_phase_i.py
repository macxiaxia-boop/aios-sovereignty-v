#!/usr/bin/env python3
"""
Phase I 验收测试 · 父线程 5 模块 (T18-T22)
由 codex 01a11c30 写 · 用户授权"全部做掉"
跑：python acceptance_phase_i.py
"""
import sys, importlib, importlib.util, traceback
from pathlib import Path

POLICY = Path(r"D:\AIOS\_agent-hub\policy")
RESULTS = []
PASS = FAIL = 0

def check(name, ok, detail=""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok: PASS += 1
    else: FAIL += 1
    print(f"  {tag}  {name}{(' — ' + detail) if detail else ''}")
    RESULTS.append((tag, name, detail))

def safe_import(name, path):
    """动态 import, 不污染 sys.path"""
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader: raise ImportError(f"spec fail: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# ==================== T18 strategy_policy.py ====================
print("\n=== T18 strategy_policy.py ===")
try:
    sp = safe_import("strategy_policy_t18", str(POLICY / "strategy_policy.py"))
    check("T18.a module loaded", True, f"{len(open(POLICY/'strategy_policy.py').read())} bytes")
    check("T18.b has load_strategy_policy", hasattr(sp, "load_strategy_policy"))
    check("T18.c has is_retired_id", hasattr(sp, "is_retired_id"))
    check("T18.d has is_industry_preset_blocked", hasattr(sp, "is_industry_preset_blocked"))
    check("T18.e has is_retired_alias", hasattr(sp, "is_retired_alias"))
    check("T18.f has is_prohibited_path", hasattr(sp, "is_prohibited_path"))
    # 实际调用
    if hasattr(sp, "load_strategy_policy"):
        try:
            policy = sp.load_strategy_policy()
            check("T18.g load_strategy_policy() returns dict", isinstance(policy, dict), f"keys={list(policy.keys())[:5]}")
        except Exception as e:
            check("T18.g load_strategy_policy() runnable", False, str(e)[:60])
except Exception as e:
    check("T18 load", False, str(e)[:100])

# ==================== T19 strategy_gate.py ====================
print("\n=== T19 strategy_gate.py ===")
try:
    sg = safe_import("strategy_gate_t19", str(POLICY / "strategy_gate.py"))
    check("T19.a module loaded", True, f"{len(open(POLICY/'strategy_gate.py').read())} bytes")
    check("T19.b has GateEvent class", hasattr(sg, "GateEvent"))
    check("T19.c has GateDecision class", hasattr(sg, "GateDecision"))
    check("T19.d has StrategyGate class", hasattr(sg, "StrategyGate"))
    check("T19.e has gate_from_policy_dir function", hasattr(sg, "gate_from_policy_dir"))
    if hasattr(sg, "gate_from_policy_dir"):
        try:
            gate = sg.gate_from_policy_dir(str(POLICY))
            check("T19.f gate_from_policy_dir returns gate", gate is not None)
        except Exception as e:
            check("T19.f gate_from_policy_dir runnable", False, str(e)[:60])
except Exception as e:
    check("T19 load", False, str(e)[:100])

# ==================== T20 requirements_lifecycle.py ====================
print("\n=== T20 requirements_lifecycle.py ===")
try:
    rl = safe_import("requirements_lifecycle_t20", str(POLICY / "requirements_lifecycle.py"))
    check("T20.a module loaded", True, f"{len(open(POLICY/'requirements_lifecycle.py').read())} bytes")
    check("T20.b has LifecycleState enum", hasattr(rl, "LifecycleState"))
    check("T20.c has Requirement class", hasattr(rl, "Requirement"))
    check("T20.d has RequirementsRegistry class", hasattr(rl, "RequirementsRegistry"))
    check("T20.e has save_registry function", hasattr(rl, "save_registry"))
    check("T20.f has load_registry function", hasattr(rl, "load_registry"))
    check("T20.g has InvalidTransition exception", hasattr(rl, "InvalidTransition"))
    check("T20.h has UnknownRequirement exception", hasattr(rl, "UnknownRequirement"))
except Exception as e:
    check("T20 load", False, str(e)[:100])

# ==================== T21 contamination_scanner.py ====================
print("\n=== T21 contamination_scanner.py ===")
try:
    cs = safe_import("contamination_scanner_t21", str(POLICY / "contamination_scanner.py"))
    check("T21.a module loaded", True, f"{len(open(POLICY/'contamination_scanner.py').read())} bytes")
    check("T21.b has Classification enum", hasattr(cs, "Classification"))
    check("T21.c has Finding class", hasattr(cs, "Finding"))
    check("T21.d has ScanReport class", hasattr(cs, "ScanReport"))
    # 找一个扫描函数
    scan_funcs = [n for n in dir(cs) if n.startswith("scan") or n.startswith("check")]
    check("T21.e has scan function", len(scan_funcs) > 0, f"found={scan_funcs[:3]}")
except Exception as e:
    check("T21 load", False, str(e)[:100])

# ==================== T22 quarantine.py ====================
print("\n=== T22 quarantine.py ===")
try:
    qz = safe_import("quarantine_t22", str(POLICY / "quarantine.py"))
    check("T22.a module loaded", True, f"{len(open(POLICY/'quarantine.py').read())} bytes")
    funcs = [n for n in dir(qz) if not n.startswith("_") and callable(getattr(qz, n))]
    check("T22.b has public functions", len(funcs) > 0, f"count={len(funcs)} sample={funcs[:3]}")
    classes = [n for n in dir(qz) if not n.startswith("_") and isinstance(getattr(qz, n), type)]
    check("T22.c has public classes", len(classes) > 0, f"count={len(classes)} sample={classes[:3]}")
except Exception as e:
    check("T22 load", False, str(e)[:100])

# ==================== SUMMARY ====================
print(f"\n=== SUMMARY: {PASS} PASS · {FAIL} FAIL · {PASS+FAIL} total ===")
sys.exit(0 if FAIL == 0 else 1)
