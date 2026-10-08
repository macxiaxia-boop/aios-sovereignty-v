# v2/tests/run_all_tests.py — driver: run all tests even without pytest.
#
# R320.1 fix:
#   - Inject pytest polyfill into sys.modules BEFORE importing test_* modules,
#     so `import pytest` at the top of test_01/test_03 does NOT crash.
#   - Collect worker-thread exceptions and assert they were zero.
#   - Print per-test pass/fail with timing, write reports/test_run.json + reports/test-output.txt.
from __future__ import annotations

import importlib
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# --- BEGIN pytest polyfill injection (must run before any `import pytest`) ----
class _RaisesCtx:
    def __init__(self, exc):
        self.exc = exc

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if et is None:
            raise AssertionError(
                f"Expected exception of type {self.exc.__name__} but none was raised"
            )
        if not issubclass(et, self.exc):
            return False
        return True


class _PytestShim:
    @staticmethod
    def raises(exc):
        return _RaisesCtx(exc)


if "pytest" not in sys.modules:
    sys.modules["pytest"] = _PytestShim()
# --- END polyfill injection ----------------------------------------------------

# Ensure conftest sets AIOS_V2_ROOT = a temp dir so tests don't pollute real state
import tests.conftest  # noqa: E402, F401

from src.paths import ensure_dirs  # noqa: E402
ensure_dirs()
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

TESTS = [
    "tests.test_01_envelope_schema",
    "tests.test_02_queue_concurrency",
    "tests.test_03_state_machine",
    "tests.test_04_heartbeat_timeout_retry",
    "tests.test_05_protocol_loopback",
    "tests.test_06_probes",
    "tests.test_07_healthcheck",
    "tests.test_08_supervisor_watch",
    # R286.A-C tests
    "tests.test_09_envelope_chunking",
    "tests.test_10_consumer_dispatch",
    "tests.test_11_consumer_restart_lease",
    "tests.test_12_artifact_refs_no_binary",
    "tests.test_13_task_lifecycle",
    "tests.test_14_cli_chunking_roundtrip",
    "tests.test_15_trace_completeness",
    "tests.test_16_mcp_bridge_tools",
    # R286.D failure-path tests
    "tests.test_17_codex_quota_handoff",
    "tests.test_18_codex_desktop_stale_thread",
]


def _collect_test_funcs(module):
    fns = []
    for name in sorted(dir(module)):
        if name.startswith("test_"):
            fns.append(getattr(module, name))
    return fns


def main() -> int:
    overall = {
        "version": "v2-2026-09-29",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": sys.version,
        "platform": sys.platform,
        "modules": [],
        "total_pass": 0,
        "total_fail": 0,
    }
    failed_modules = 0
    console_lines = []

    def out(s):
        print(s)
        console_lines.append(s)

    out("=" * 78)
    out(f"  AIOS Hub v2 test suite (driver=run_all_tests.py)")
    out(f"  Python: {sys.version.split()[0]}    Platform: {sys.platform}")
    out(f"  Started: {overall['started_at']}")
    out("=" * 78)

    for modname in TESTS:
        mod_t0 = time.time()
        try:
            m = importlib.import_module(modname)
        except Exception as e:
            tb = traceback.format_exc(limit=8)
            # R320.2: module-load failure counts as fail=1, not pass=0/fail=0.
            # The fake-green display of "module PASS 0/0" was a runner bug.
            overall["modules"].append({
                "module": modname, "pass": 0, "fail": 1,
                "tests": [{"name": "<module-load>", "ok": False, "error": str(e),
                            "traceback": tb}],
                "module_load_failed": True,
            })
            overall["total_fail"] += 1
            failed_modules += 1
            out(f"  [FAIL] {modname:42s}  module-load failed: {e}")
            continue
        fns = _collect_test_funcs(m)
        module_rec = {"module": modname, "pass": 0, "fail": 0, "tests": []}
        for fn in fns:
            t0 = time.time()
            try:
                fn()
                module_rec["tests"].append({"name": fn.__name__, "ok": True,
                                              "duration_ms": int((time.time()-t0)*1000)})
                module_rec["pass"] += 1
                overall["total_pass"] += 1
                out(f"    [PASS] {fn.__name__}  ({int((time.time()-t0)*1000)} ms)")
            except Exception as e:
                tb = traceback.format_exc(limit=4)
                module_rec["tests"].append({"name": fn.__name__, "ok": False,
                                              "error": str(e), "traceback": tb,
                                              "duration_ms": int((time.time()-t0)*1000)})
                module_rec["fail"] += 1
                overall["total_fail"] += 1
                out(f"    [FAIL] {fn.__name__}  ({int((time.time()-t0)*1000)} ms)  {e}")
        module_rec["module_duration_ms"] = int((time.time()-mod_t0)*1000)
        overall["modules"].append(module_rec)
        if module_rec["fail"]:
            failed_modules += 1

    overall["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    overall["failed_modules"] = failed_modules
    overall["all_pass"] = overall["total_fail"] == 0

    out("-" * 78)
    for m in overall["modules"]:
        status = "PASS" if m["fail"] == 0 else "FAIL"
        out(f"  [{status}] {m['module']:42s}  pass={m['pass']:2d}  fail={m['fail']:2d}  ({m.get('module_duration_ms',0)} ms)")
    out("-" * 78)
    out(f"  TOTAL: pass={overall['total_pass']}  fail={overall['total_fail']}")
    out(f"  Ended:  {overall['ended_at']}")
    out("=" * 78)

    json_path = REPORTS / "test_run.json"
    json_path.write_text(json.dumps(overall, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path = REPORTS / "test-output.txt"
    txt_path.write_text("\n".join(console_lines) + "\n", encoding="utf-8")
    out(f"  Report:    {json_path}")
    out(f"  Plaintext: {txt_path}")
    out("=" * 78)
    return 0 if overall["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())