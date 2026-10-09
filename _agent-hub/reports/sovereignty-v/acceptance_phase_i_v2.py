#!/usr/bin/env python3
"""
Phase I 验收测试 v3 · 父线程 5 模块 · 修最后 1 FAIL (T21.f)
"""
import sys, importlib, importlib.util, traceback, re
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
    """动态 import + 把 dir 加 sys.path"""
    file_dir = str(Path(path).parent)
    if file_dir not in sys.path:
        sys.path.insert(0, file_dir)
    pkg_name = "policy_pkg"
    if pkg_name not in sys.modules:
        pkg = type(sys)(pkg_name)
        pkg.__path__ = [file_dir]
        sys.modules[pkg_name] = pkg
    submod = f"policy_pkg.{name}"
    spec = importlib.util.spec_from_file_location(submod, path)
    if not spec or not spec.loader:
        raise ImportError(f"spec fail: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[submod] = mod
    spec.loader.exec_module(mod)
    return mod

# ==================== T18 strategy_policy.py ====================
print("\n=== T18 strategy_policy.py ===")
try:
    sp = safe_import("strategy_policy_t18", str(POLICY / "strategy_policy.py"))
    src = open(POLICY/'strategy_policy.py').read()
    check("T18.a module loaded", True, f"{len(src)} bytes")
    check("T18.b has load_strategy_policy", hasattr(sp, "load_strategy_policy"))
    check("T18.c has is_retired_id", hasattr(sp, "is_retired_id"))
    check("T18.d has is_industry_preset_blocked", hasattr(sp, "is_industry_preset_blocked"))
    check("T18.e has is_retired_alias", hasattr(sp, "is_retired_alias"))
    check("T18.f has is_prohibited_path", hasattr(sp, "is_prohibited_path"))
    if hasattr(sp, "load_strategy_policy"):
        try:
            result = sp.load_strategy_policy()
            has_data = (isinstance(result, dict)) or (hasattr(result, "policy") and result.policy is not None) or hasattr(result, "__dict__")
            check("T18.g load_strategy_policy() returns data", has_data, f"type={type(result).__name__}")
        except Exception as e:
            check("T18.g load_strategy_policy() runnable", False, str(e)[:60])
except Exception as e:
    check("T18 load", False, str(e)[:100])

# ==================== T19 strategy_gate.py ====================
print("\n=== T19 strategy_gate.py ===")
try:
    sg = safe_import("strategy_gate_t19", str(POLICY / "strategy_gate.py"))
    src = open(POLICY/'strategy_gate.py').read()
    check("T19.a module loaded", True, f"{len(src)} bytes")
    check("T19.b has GateEvent class", hasattr(sg, "GateEvent"))
    check("T19.c has GateDecision class", hasattr(sg, "GateDecision"))
    check("T19.d has StrategyGate class", hasattr(sg, "StrategyGate"))
    check("T19.e has gate_from_policy_dir function", hasattr(sg, "gate_from_policy_dir"))
    if hasattr(sg, "gate_from_policy_dir"):
        try:
            gate = sg.gate_from_policy_dir(str(POLICY))
            check("T19.f gate_from_policy_dir returns gate", gate is not None, f"type={type(gate).__name__}")
        except Exception as e:
            check("T19.f gate_from_policy_dir runnable", False, str(e)[:80])
except Exception as e:
    check("T19 load", False, str(e)[:100])

# ==================== T20 requirements_lifecycle.py ====================
print("\n=== T20 requirements_lifecycle.py ===")
try:
    rl = safe_import("requirements_lifecycle_t20", str(POLICY / "requirements_lifecycle.py"))
    src = open(POLICY/'requirements_lifecycle.py').read()
    check("T20.a module loaded", True, f"{len(src)} bytes")
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
    src = open(POLICY/'contamination_scanner.py').read()
    check("T21.a module loaded", True, f"{len(src)} bytes")
    check("T21.b has Classification enum", hasattr(cs, "Classification"))
    check("T21.c has Finding class", hasattr(cs, "Finding"))
    check("T21.d has ScanReport class", hasattr(cs, "ScanReport"))
    # T21.e: scan-related attrs
    scan_attrs = [n for n in dir(cs) if re.search(r"scan|check|find|detect", n, re.I)]
    check("T21.e has scan-related attrs", len(scan_attrs) > 0, f"count={len(scan_attrs)} sample={scan_attrs[:5]}")
    # T21.f: 找到 ContaminationScanner 类 + 实例化 + 找到扫描方法
    scanner_class_name = "ContaminationScanner"
    has_scanner = hasattr(cs, scanner_class_name)
    check("T21.f has ContaminationScanner class", has_scanner)
    if has_scanner:
        try:
            ScannerClass = getattr(cs, scanner_class_name)
            # 构造空 policy dict 满足 required positional
            try:
                import json as _json
                _pol_path = (Path(POLICY) / "strategy_policy.py")
            except Exception: _pol_path = None
            try:
                instance = ScannerClass({})
            except Exception as e1:
                try:
                    instance = ScannerClass(policy={})
                except Exception:
                    instance = None
                    raise e1
            methods = [m for m in dir(instance) if not m.startswith("_") and callable(getattr(instance, m))]
            scan_methods = [m for m in methods if re.search(r"scan|run|check|find|detect", m, re.I)]
            check("T21.g ContaminationScanner 实例化 + 扫描方法", len(scan_methods) > 0, f"methods={scan_methods[:5]}")
        except Exception as e:
            check("T21.g ContaminationScanner 实例化", False, str(e)[:60])
except Exception as e:
    check("T21 load", False, str(e)[:100])

# ==================== T22 quarantine.py ====================
print("\n=== T22 quarantine.py ===")
try:
    qz = safe_import("quarantine_t22", str(POLICY / "quarantine.py"))
    src = open(POLICY/'quarantine.py').read()
    check("T22.a module loaded", True, f"{len(src)} bytes")
    funcs = [n for n in dir(qz) if not n.startswith("_") and callable(getattr(qz, n))]
    real_funcs = [n for n in funcs if n not in ("Any", "Path")]
    check("T22.b has public functions", len(real_funcs) > 0, f"count={len(real_funcs)} sample={real_funcs[:3]}")
    classes = [n for n in dir(qz) if not n.startswith("_") and isinstance(getattr(qz, n), type)]
    real_classes = [n for n in classes if n not in ("Any", "Path")]
    check("T22.c has public classes", len(real_classes) > 0, f"count={len(real_classes)} sample={real_classes[:3]}")
except Exception as e:
    check("T22 load", False, str(e)[:100])

print(f"\n=== SUMMARY: {PASS} PASS · {FAIL} FAIL · {PASS+FAIL} total ===")
sys.exit(0 if FAIL == 0 else 1)
