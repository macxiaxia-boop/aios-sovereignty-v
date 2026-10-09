"""test_simulation_e2e.py - End-to-end test of the T0040 simulation harness.

What it exercises (in one test session, must finish in < 60 wall-clock seconds):

1. Determinism:
     build_mock_tasks(seed=42) called twice -> identical results.
2. Worker coverage:
     All 6 mock workers (Success/FakeDone/Crash/Timeout/RetryableFail/PermanentFail)
     behave per their contract.
3. Evidence + Verifier:
     SuccessWorker artifacts pass verifier; FakeDone artifacts fail; tampering
     forces a PASS->FAIL flip.
4. Time compression:
     MockClock.advance_days(21) crosses 3 weeks of business simulation in one call.
5. Crash injector:
     5 sequential kill+restart cycles preserve kernel handle state (mirrors T0037 CR7).
6. Runner integration:
     runner.run_all_acceptance_tests() returns 10/10 PASS and writes a JSON report.
7. Wall-clock budget:
     The whole test must finish in < 60 s — recorded as `wall_clock_seconds`.

Run with: python tests/sim/test_simulation_e2e.py
          or
          pytest tests/sim/test_simulation_e2e.py -v
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Bootstrap sys.path so we can `import tests.sim.mocks.*` from any cwd.
_THIS = Path(__file__).resolve()
_KERNEL_ROOT = _THIS.parents[2]
if str(_KERNEL_ROOT) not in sys.path:
    sys.path.insert(0, str(_KERNEL_ROOT))

from tests.sim.mocks.crash_injector import (  # noqa: E402
    CrashInjector,
    KernelHandle,
)
from tests.sim.mocks.mock_clock import MockClock  # noqa: E402
from tests.sim.mocks.mock_evidence import (  # noqa: E402
    EvidenceRecord,
    MockEvidenceStore,
    verify_worker_evidence,
)
from tests.sim.mocks.mock_tasks import (  # noqa: E402
    SEED,
    TASK_TYPES,
    TOTAL_TASKS,
    build_mock_tasks,
    build_mock_tasks_by_type,
)
from tests.sim.mocks.mock_workers import (  # noqa: E402
    CrashWorker,
    FakeDoneWorker,
    PermanentFailWorker,
    RetryableFailWorker,
    SuccessWorker,
    TimeoutWorker,
    WorkerCrashException,
    WorkerResult,
)
from tests.sim.runner import run_all_acceptance_tests  # noqa: E402


class TestFailure(AssertionError):
    pass


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise TestFailure(msg)


def run_e2e() -> Dict[str, Any]:
    """Run the full e2e and return a result dict (also written to disk)."""
    wall_start = time.perf_counter()
    checks: List[Dict[str, Any]] = []

    # ---- 1. determinism -------------------------------------------------
    t_a = build_mock_tasks(seed=SEED)
    t_b = build_mock_tasks(seed=SEED)
    deterministic = (
        len(t_a) == len(t_b) == TOTAL_TASKS
        and all(x.id == y.id and x.budget == y.budget for x, y in zip(t_a, t_b))
    )
    by_type = build_mock_tasks_by_type(seed=SEED)
    types_ok = all(len(v) == 20 for v in by_type.values())
    _assert(deterministic, "tasks not deterministic across same seed")
    _assert(types_ok, "task distribution != 5 types x 20")
    checks.append({"check": "determinism_100_tasks_5x20", "passed": True,
                   "expected": TOTAL_TASKS, "observed": len(t_a)})

    # ---- 2. worker coverage ---------------------------------------------
    sample = t_a[0].to_dict()
    success = SuccessWorker().execute(sample)
    _assert(success.success and success.artifact and success.artifact.evidence_ids,
            "SuccessWorker must return artifact + evidence_ids")

    fake = FakeDoneWorker().execute(sample)
    _assert(fake.success and fake.artifact and not fake.artifact.evidence_ids,
            "FakeDoneWorker must return success=True but empty evidence_ids")

    try:
        _ = CrashWorker().execute(sample)
        raised = False
    except WorkerCrashException:
        raised = True
    _assert(raised, "CrashWorker must raise WorkerCrashException")

    timeout = TimeoutWorker()
    timeout.default_timeout_s = 0.01
    tout = timeout.execute(sample)
    _assert(tout.timed_out and not tout.success, "TimeoutWorker must report timed_out")

    retry = RetryableFailWorker()
    r1 = retry.execute(sample)
    r2 = retry.execute(sample)
    r3 = retry.execute(sample)
    _assert(
        not r1.success and not r2.success and r3.success,
        f"RetryableFailWorker wrong: r1={r1.success} r2={r2.success} r3={r3.success}",
    )
    _assert(r3.attempts == 3, f"RetryableFailWorker attempt count: {r3.attempts}")

    perm = PermanentFailWorker().execute(sample)
    _assert(not perm.success, "PermanentFailWorker must always fail")
    checks.append({"check": "worker_coverage_6_types", "passed": True})

    # ---- 3. evidence + verifier -----------------------------------------
    store = MockEvidenceStore()
    # Put SuccessWorker evidence into the store before asking the verifier
    # to check it. FakeDoneWorker produces empty evidence_ids, so the
    # verifier can reject it without us putting anything into the store.
    for eid in success.artifact.evidence_ids:
        store.put(EvidenceRecord(
            id=eid,
            task_id=sample["id"],
            artifact_id=success.artifact.id,
            payload="success_payload",
            signed_at=datetime.now(timezone.utc).isoformat(),
            verdict="PENDING",
        ))
    # also stash a tampered record for the corruption test
    tampered_id = "ev-tamper"
    store.put(EvidenceRecord(
        id=tampered_id,
        task_id=sample["id"],
        artifact_id="art-x",
        payload="legit_at_put",
        signed_at=datetime.now(timezone.utc).isoformat(),
        verdict="PENDING",
    ))
    _assert(store.verify(success.artifact.evidence_ids[0]),
            "freshly-stored SuccessWorker evidence must verify")
    _assert(store.verify(tampered_id), "freshly-stored evidence must verify")

    store.tamper(tampered_id)
    _assert(not store.verify(tampered_id), "tampered evidence must NOT verify")

    # FalseCompletion -> verifier must reject (empty evidence_ids)
    vf = verify_worker_evidence(store, fake.artifact.evidence_ids)
    _assert(vf["verdict"] != "PASS", "FakeDoneWorker must be rejected by verifier")

    # legit SuccessWorker artifact -> verifier PASS
    vok = verify_worker_evidence(store, success.artifact.evidence_ids)
    _assert(vok["verdict"] == "PASS", f"SuccessWorker artifacts must PASS, got {vok}")
    checks.append({"check": "evidence_verify_tamper_reject", "passed": True})

    # ---- 4. time compression --------------------------------------------
    clock = MockClock()
    before_iso = clock.now().isoformat()
    after_dt = clock.advance_days(21)  # 3 simulated weeks
    after_iso = after_dt.isoformat()
    _assert(after_iso != before_iso, "advance_days must move the clock")
    _assert(clock.time_compression == 86400,
            f"time_compression must default to 86400, got {clock.time_compression}")
    checks.append({"check": "time_compression_3_weeks", "passed": True,
                   "weeks_simulated": 3, "compression": clock.time_compression})

    # ---- 5. crash injector (T0037 CR7) ----------------------------------
    inj = CrashInjector(clock=MockClock())
    handle = inj.spawn(initial_pid=12345, state={"recovered": 0})

    def recover_fn(kh: KernelHandle) -> None:
        kh.state["recovered"] = kh.state.get("recovered", 0) + 1

    inj.kill_and_restart(handle, count=5, between_sleep_s=0.0, recover_fn=recover_fn)
    s = inj.summary()
    _assert(s["kills"] == 5 and s["restarts"] == 5,
            f"CR7 expected 5 kills + 5 restarts, got {s}")
    _assert(handle.state["recovered"] == 5,
            f"state.recovered must equal 5, got {handle.state['recovered']}")
    checks.append({"check": "crash_5x_kill_restart_state_persists", "passed": True,
                   "kills": s["kills"], "restarts": s["restarts"]})

    # ---- 6. runner integration ------------------------------------------
    runner_report = run_all_acceptance_tests()
    _assert(runner_report["criteria_total"] == 10, "runner must report 10 criteria")
    _assert(runner_report["criteria_passed"] == 10,
            f"all 10 must pass, got {runner_report['criteria_passed']}")
    checks.append({"check": "runner_10/10_pass", "passed": True,
                   "passed": runner_report["criteria_passed"],
                   "total": runner_report["criteria_total"]})

    # ---- 7. write JSON report + budget assertion -----------------------
    wall = time.perf_counter() - wall_start
    report = {
        "schema_version": "1.0",
        "title": "T0040 simulation harness e2e",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "wall_clock_seconds": round(wall, 4),
        "checks": checks,
        "all_passed": True,
        "runner_summary": {
            "criteria_total": runner_report["criteria_total"],
            "criteria_passed": runner_report["criteria_passed"],
            "criteria_failed": runner_report["criteria_failed"],
            "wall_clock_seconds": runner_report["wall_clock_seconds"],
        },
        "time_compression": runner_report["time_compression"],
    }
    report_path = _THIS.parent / "test_simulation_e2e_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _assert(wall < 60.0, f"e2e must finish in <60s, took {wall:.2f}s")
    return report


def main() -> int:
    try:
        report = run_e2e()
    except TestFailure as tf:
        print(f"FAIL: {tf}", file=sys.stderr)
        traceback.print_exc()
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 2

    print(f"PASS: wall={report['wall_clock_seconds']}s "
          f"checks={len(report['checks'])} "
          f"runner={report['runner_summary']['criteria_passed']}/"
          f"{report['runner_summary']['criteria_total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())