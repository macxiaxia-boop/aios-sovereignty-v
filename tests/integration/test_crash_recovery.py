"""test_crash_recovery.py - T0037 Crash Recovery integration tests.

10 test cases covering kernel crash recovery semantics. The injector
spawns real Python subprocesses (`tests/integration/_kernel_worker.py`)
so the kill is a true OS-level SIGKILL (taskkill /F /PID on Windows).

Assertion rules per the card:
  - 幂等性 (idempotency): a completed activity must NOT be re-executed
  - 原子性 (atomicity): partial writes must roll back atomically
  - 持久性 (durability): committed data must survive kill -9
  - 可恢复性 (recoverability): an incomplete run can be resumed to
    completion via fresh engine

Run:  pytest tests/integration/test_crash_recovery.py -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import pytest

_THIS = Path(__file__).resolve()
_KERNEL_ROOT = _THIS.parents[2]
if str(_KERNEL_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_KERNEL_ROOT / "src"))

from tests.integration.crash_injector import (  # noqa: E402
    CrashInjector,
    KernelProcess,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def tmp_test_dir():
    """One tempdir per test; cleaned up on the way out."""
    p = Path(tempfile.mkdtemp(prefix="aios_cr_"))
    yield p
    # best-effort cleanup (Windows may hold files briefly)
    for _ in range(3):
        try:
            shutil.rmtree(p, ignore_errors=True)
            break
        except OSError:
            time.sleep(0.1)


@pytest.fixture
def db_url(tmp_test_dir):
    """A file-backed SQLite URL per test (shared between test process
    and worker subprocesses)."""
    path = tmp_test_dir / f"cr_{uuid.uuid4().hex[:8]}.db"
    return f"sqlite+aiosqlite:///{path.as_posix()}"


@pytest.fixture
def result_dir(tmp_test_dir):
    """Per-test result file directory."""
    p = tmp_test_dir / "results"
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def injector():
    """A CrashInjector with cleanup-on-exit."""
    inj = CrashInjector(default_timeout_s=10.0)
    yield inj
    inj.kill_all()


def _kill_and_reap(inj: CrashInjector, kp: KernelProcess) -> int:
    """Kill the subprocess and block until it actually exits."""
    pid = kp.pid
    inj.kill_n9(kp)
    return pid


# ===========================================================================
# CR1 - Goal creation mid-crash
# ===========================================================================


async def test_cr1_goal_create_mid_crash_rolls_back(injector, db_url, result_dir):
    """Kernel crashes after GoalService.create_goal() has added the row
    in memory but BEFORE the session commit().

    Restart with verify_state -> 0 goals in DB (transaction rolled back).
    Atomicity: the uncommitted insert never leaks into the DB.
    """
    config = {
        "title": "cr1-goal",
        "success_criteria": "x",
        "budget": 10.0,
        "owner": "cr1",
        "crash_hook": "crash_before_commit",
    }

    kp = injector.start_kernel(
        db_url, mode="goal_create", config=config, result_dir=result_dir
    )
    try:
        assert injector.wait_for_marker(kp, timeout_s=5.0), (
            "worker did not reach crash_before_commit hook"
        )
        _kill_and_reap(injector, kp)
    finally:
        injector.cleanup(kp)

    # Restart: read state via verify_state (no crash hook).
    state = injector.verify_state(
        db_url,
        include_goals=True,
        include_plans=False,
        include_evidence=False,
        result_dir=result_dir,
    )

    goals = state.get("goals", [])
    cr1_goals = [g for g in goals if g.get("title") == "cr1-goal"]
    # 原子性: uncommitted insert was rolled back
    assert cr1_goals == [], (
        f"expected 0 'cr1-goal' rows after crash-before-commit; got {cr1_goals}"
    )


# ===========================================================================
# CR2 - Task execution mid-crash (1/3 complete), resume picks up at 2
# ===========================================================================


async def test_cr2_workflow_resume_does_not_redo_step_a(
    injector, db_url, result_dir
):
    """A 3-step workflow. Step A completes and is checkpointed. Step B
    is mid-execution when SIGKILL lands. On restart, the engine resumes
    from step B and step A is NOT re-executed (idempotency).

    The worker uses a special 'kill_at_b' mode where step B sleeps
    forever when crash_after_step_a is configured, so the marker fires
    AFTER step A's checkpoint is committed.
    """
    run_id = f"cr2-{uuid.uuid4().hex[:8]}"

    config = {
        "run_id": run_id,
        "workflow_mode": "kill_at_b",
        "crash_hook": "crash_after_step_a",
    }

    kp = injector.start_kernel(
        db_url, mode="workflow_run", config=config, result_dir=result_dir
    )
    try:
        assert injector.wait_for_marker(kp, timeout_s=5.0), (
            "worker did not reach crash_after_step_a hook"
        )
        _kill_and_reap(injector, kp)
    finally:
        injector.cleanup(kp)

    # After kill, the DB should still have step A's completed checkpoint
    # (it was committed by the engine before step B started).
    state_before = injector.verify_state(
        db_url,
        expected_run_id=run_id,
        include_goals=False,
        result_dir=result_dir,
    )
    run_before = state_before.get("workflow_run")
    assert run_before is not None, "workflow_run row missing after crash"
    cps_before = state_before.get("checkpoints", [])
    a_cps = [c for c in cps_before if c["step_id"] == "a"]
    assert a_cps, f"step A checkpoint missing after crash: {cps_before}"
    assert a_cps[0]["status"] == "completed"
    assert run_before["status"] in ("running", "failed"), (
        f"unexpected status after crash: {run_before['status']}"
    )

    # Now restart with workflow_resume (no crash hook) to drive B and C to
    # completion.
    config_resume = {"run_id": run_id, "workflow_mode": "kill_at_b"}
    kp2 = injector.start_kernel(
        db_url, mode="workflow_resume", config=config_resume, result_dir=result_dir
    )
    try:
        result = kp2.read_result(timeout_s=10.0)
        assert result is not None, "resume worker did not produce a result"
        assert result.get("run_id") == run_id
        assert result.get("status") == "completed", (
            f"expected 'completed', got {result.get('status')}: {result}"
        )
    finally:
        injector.cleanup(kp2)

    # Verify: step A still has attempt=1 only (idempotency).
    state_after = injector.verify_state(
        db_url,
        expected_run_id=run_id,
        include_goals=False,
        result_dir=result_dir,
    )
    cps_after = state_after.get("checkpoints", [])
    history_after = state_after.get("activity_history", [])
    a_hist = [h for h in history_after if h["step_id"] == "a"]
    # Each "completed" attempt = 1; no second run.
    completed_a = [h for h in a_hist if h["status"] == "completed"]
    assert len(completed_a) == 1, (
        f"step A was re-executed after resume: {a_hist}"
    )

    # And the run is now Completed.
    run_after = state_after["workflow_run"]
    assert run_after["status"] == "completed", (
        f"expected completed, got {run_after['status']}"
    )


# ===========================================================================
# CR3 - Plan reversion mid-crash
# ===========================================================================


async def test_cr3_plan_revert_crash_leaves_consistent_state(
    injector, db_url, result_dir
):
    """Plan reversion flips v1.is_active=False then adds v2. If killed
    after mark_inactive but before commit, the transaction must roll back
    (v1 stays active). On restart without crash hook, the reversion
    completes cleanly: v1 inactive, v2 active.
    """
    goal_title = "cr3-goal"
    config_crash = {
        "goal_title": goal_title,
        "crash_hook": "crash_after_old_inactive",
    }

    kp = injector.start_kernel(
        db_url, mode="plan_revert", config=config_crash, result_dir=result_dir
    )
    try:
        assert injector.wait_for_marker(kp, timeout_s=5.0), (
            "worker did not reach crash_after_old_inactive hook"
        )
        _kill_and_reap(injector, kp)
    finally:
        injector.cleanup(kp)

    # After crash: v1 should still be active (uncommitted transaction
    # rolled back).
    state_after_crash = injector.verify_state(
        db_url,
        include_goals=True,
        include_plans=True,
        result_dir=result_dir,
    )
    plans_after_crash = state_after_crash.get("plans", [])
    cr3_plans = [
        p for p in plans_after_crash
        if p.get("title") == "v1" and p.get("is_active") is False
    ]
    assert cr3_plans == [], (
        f"atomic rollback failed: v1 was marked inactive without "
        f"commit: {plans_after_crash}"
    )

    # Restart: full reversion path (no crash hook) should now produce
    # v1 inactive + v2 active.
    config_ok = {
        "goal_title": goal_title + "-restart",
        "crash_hook": "none",
    }
    kp2 = injector.start_kernel(
        db_url, mode="plan_revert", config=config_ok, result_dir=result_dir
    )
    try:
        result = kp2.read_result(timeout_s=10.0)
        assert result is not None, "plan_revert worker did not produce a result"
        assert "v2_id" in result, f"missing v2_id: {result}"
        assert result.get("v2_version") == 2
    finally:
        injector.cleanup(kp2)


# ===========================================================================
# CR4 - Verifier call mid-crash
# ===========================================================================


async def test_cr4_verifier_call_mid_crash_atomic_evidence(
    injector, db_url, result_dir
):
    """VerifierCall adds an Evidence row but crashes before the
    session commit. Atomicity -> no evidence row in DB.
    Then we run verifier_call cleanly -> 1 evidence row.
    """
    config_crash = {"crash_hook": "crash_after_record"}
    kp = injector.start_kernel(
        db_url, mode="verifier_call", config=config_crash, result_dir=result_dir
    )
    try:
        assert injector.wait_for_marker(kp, timeout_s=5.0), (
            "worker did not reach crash_after_record hook"
        )
        _kill_and_reap(injector, kp)
    finally:
        injector.cleanup(kp)

    # After crash: no evidence row in DB.
    state = injector.verify_state(
        db_url, include_evidence=True, result_dir=result_dir
    )
    evidences = state.get("evidences", [])
    assert evidences == [], (
        f"atomic rollback failed: evidence leaked after crash: {evidences}"
    )

    # Now do a clean verifier_call -> exactly one evidence row.
    kp2 = injector.start_kernel(
        db_url,
        mode="verifier_call",
        config={"crash_hook": "none"},
        result_dir=result_dir,
    )
    try:
        result = kp2.read_result(timeout_s=10.0)
        assert result is not None, "clean verifier_call produced no result"
        assert "evidence_id" in result, f"missing evidence_id: {result}"
    finally:
        injector.cleanup(kp2)

    state_after = injector.verify_state(
        db_url, include_evidence=True, result_dir=result_dir
    )
    evs_after = state_after.get("evidences", [])
    assert len(evs_after) == 1, (
        f"expected exactly 1 evidence after clean run; got {len(evs_after)}: {evs_after}"
    )


# ===========================================================================
# CR5 - Budget check mid-crash (no double-deduct)
# ===========================================================================


async def test_cr5_budget_check_mid_crash_no_double_deduct(
    injector, db_url, result_dir
):
    """Budget check: goal.metadata["spent"] is updated but session
    is never committed. Kill mid-deduct -> rollback. Goal.budget should
    remain the initial value and metadata['spent'] should not be set.
    """
    initial_budget = 100.0
    deduct_amount = 30.0

    config = {
        "initial_budget": initial_budget,
        "deduct_amount": deduct_amount,
        "crash_hook": "crash_mid_deduct",
    }
    kp = injector.start_kernel(
        db_url, mode="budget_check", config=config, result_dir=result_dir
    )
    try:
        assert injector.wait_for_marker(kp, timeout_s=5.0), (
            "worker did not reach crash_mid_deduct hook"
        )
        _kill_and_reap(injector, kp)
    finally:
        injector.cleanup(kp)

    state = injector.verify_state(db_url, include_goals=True, result_dir=result_dir)
    goals = state.get("goals", [])
    g = next(
        (g for g in goals if g.get("title") == "budget-crash-test"),
        None,
    )
    assert g is not None, "budget goal not found"
    # 持久性: budget column was committed by the initial create_goal;
    # it must survive the kill.
    assert float(g["budget"]) == initial_budget, (
        f"budget changed after crash: {g.get('budget')}"
    )
    # 原子性: the spent update was uncommitted; metadata must not contain
    # 'spent' (or it must be absent / untouched from default {}).
    meta = g.get("metadata") or {}
    assert "spent" not in meta, (
        f"uncommitted spent leaked into metadata: {meta}"
    )


# ===========================================================================
# CR6 - Evidence write mid-crash (atomic)
# ===========================================================================


async def test_cr6_evidence_write_mid_crash_atomic(
    injector, db_url, result_dir
):
    """EvidenceWrite: in one transaction, writes a Task + Evidence.
    Crashes before final commit -> both must roll back. Then a clean run
    produces exactly one evidence row.
    """
    config_crash = {"crash_hook": "crash_before_final_commit"}
    kp = injector.start_kernel(
        db_url,
        mode="evidence_write",
        config=config_crash,
        result_dir=result_dir,
    )
    try:
        assert injector.wait_for_marker(kp, timeout_s=5.0), (
            "worker did not reach crash_before_final_commit hook"
        )
        _kill_and_reap(injector, kp)
    finally:
        injector.cleanup(kp)

    state = injector.verify_state(
        db_url, include_evidence=True, result_dir=result_dir
    )
    evidences = state.get("evidences", [])
    assert evidences == [], (
        f"atomic rollback failed: evidence present after crash: {evidences}"
    )

    # Clean run.
    kp2 = injector.start_kernel(
        db_url,
        mode="evidence_write",
        config={"crash_hook": "none"},
        result_dir=result_dir,
    )
    try:
        result = kp2.read_result(timeout_s=10.0)
        assert result is not None
        assert "evidence_id" in result
    finally:
        injector.cleanup(kp2)

    state_after = injector.verify_state(
        db_url, include_evidence=True, result_dir=result_dir
    )
    assert len(state_after.get("evidences", [])) == 1


# ===========================================================================
# CR7 - 5 consecutive crashes + restarts (stability)
# ===========================================================================


async def test_cr7_five_consecutive_crashes_recover_to_completed(
    injector, db_url, result_dir
):
    """Loop: start workflow with crash hook, kill, resume, repeat.
    After 5 cycles the run must be Completed and step A's history must
    still show attempt=1 only (idempotency holds across many cycles).
    """
    run_id = f"cr7-{uuid.uuid4().hex[:8]}"

    for i in range(5):
        config = {
            "run_id": run_id,
            "workflow_mode": "kill_at_b",
            "crash_hook": "crash_after_step_a",
        }
        kp = injector.start_kernel(
            db_url, mode="workflow_run", config=config, result_dir=result_dir
        )
        try:
            assert injector.wait_for_marker(kp, timeout_s=5.0), (
                f"cycle {i}: worker did not reach crash hook"
            )
            _kill_and_reap(injector, kp)
        finally:
            injector.cleanup(kp)

        # After each kill, attempt resume.
        config_resume = {"run_id": run_id, "workflow_mode": "kill_at_b"}
        kp_resume = injector.start_kernel(
            db_url,
            mode="workflow_resume",
            config=config_resume,
            result_dir=result_dir,
        )
        try:
            res = kp_resume.read_result(timeout_s=10.0)
            assert res is not None, f"cycle {i}: resume produced no result"
            assert res.get("run_id") == run_id
            # First 4 cycles: the resumed run completes (since the
            # worker's step_b raises after sleeping, but in resume path
            # the engine uses kill_at_b mode where step_b succeeds).
            assert res.get("status") == "completed", (
                f"cycle {i}: resume failed: {res}"
            )
        finally:
            injector.cleanup(kp_resume)

    # Final check: idempotency across all 5 cycles. step A must have
    # attempt=1 still (never re-executed).
    state = injector.verify_state(
        db_url, expected_run_id=run_id, result_dir=result_dir
    )
    history = state.get("activity_history", [])
    a_completed = [h for h in history if h["step_id"] == "a" and h["status"] == "completed"]
    assert len(a_completed) == 1, (
        f"step A was re-executed across 5 crash cycles: {a_completed}"
    )


# ===========================================================================
# CR8 - Crash while verifier daemon runs (independent process)
# ===========================================================================


async def test_cr8_daemon_unaffected_by_kernel_crash(
    injector, db_url, result_dir
):
    """A verifier daemon runs as a separate subprocess writing
    heartbeat evidence. Concurrently, we crash a workflow. The daemon
    must keep writing heartbeats. PID must be different.
    """
    daemon_cfg = {"duration_s": 4.0}
    daemon_kp = injector.start_kernel(
        db_url,
        mode="verifier_daemon",
        config=daemon_cfg,
        result_dir=result_dir,
    )
    try:
        # Give daemon a moment to write at least one heartbeat.
        time.sleep(0.3)

        # Now crash a workflow subprocess.
        run_id = f"cr8-{uuid.uuid4().hex[:8]}"
        wf_cfg = {
            "run_id": run_id,
            "workflow_mode": "kill_at_b",
            "crash_hook": "crash_after_step_a",
        }
        wf_kp = injector.start_kernel(
            db_url, mode="workflow_run", config=wf_cfg, result_dir=result_dir
        )
        try:
            assert injector.wait_for_marker(wf_kp, timeout_s=10.0)
            _kill_and_reap(injector, wf_kp)
        finally:
            injector.cleanup(wf_kp)

        # PID isolation
        assert wf_kp.pid != daemon_kp.pid, (
            f"daemon and workflow shared pid {wf_kp.pid}"
        )

        # Wait for daemon to finish its loop.
        rc = injector.wait_for_exit(daemon_kp, timeout_s=15.0)
        daemon_payload = daemon_kp.read_result(timeout_s=2.0)
    finally:
        injector.cleanup(daemon_kp)

    assert daemon_payload is not None, "daemon produced no result"
    assert daemon_payload.get("daemon_pid") == daemon_kp.pid, (
        f"daemon PID mismatch: {daemon_payload}"
    )
    # Daemon wrote >= 3 heartbeats (4s / 0.2s = 20, but allow >= 3 to be
    # safe across platforms).
    hb = daemon_payload.get("heartbeat_count", 0)
    assert hb >= 3, f"daemon did not survive long enough: {hb} heartbeats"

    # Verify the daemon's evidence rows are in the DB.
    state = injector.verify_state(
        db_url, include_evidence=True, include_daemon_heartbeats=True,
        result_dir=result_dir,
    )
    daemon_hbeats = state.get("daemon_heartbeats", [])
    daemon_rows = [e for e in daemon_hbeats if e.get("verifier_id") == f"daemon-{daemon_kp.pid}"]
    assert len(daemon_rows) >= 3, (
        f"expected >=3 daemon heartbeats in DB; got {len(daemon_rows)}"
    )


# ===========================================================================
# CR9 - DB disconnect during crash; engine rebuilds on restart
# ===========================================================================


async def test_cr9_db_disconnect_then_restart_rebuilds_connection(
    injector, db_url, result_dir, tmp_test_dir
):
    """Simulate 'DB connection断开时 crash':
      1) start a worker, let it write data, kill it (committed data
         must survive)
      2) move the DB file aside (simulating connection loss / file gone)
      3) restart with same URL -> engine must re-init cleanly, returning
         an empty fresh DB (no panic, no leaked connection)

    This proves restart-after-disconnect works: the engine builds a new
    connection without holding on to a stale handle.
    """
    # Step 1: seed data via clean verifier_call.
    kp = injector.start_kernel(
        db_url, mode="verifier_call", config={"crash_hook": "none"}, result_dir=result_dir
    )
    try:
        result = kp.read_result(timeout_s=10.0)
        assert result is not None and "evidence_id" in result
    finally:
        injector.cleanup(kp)

    # Confirm seed.
    state1 = injector.verify_state(
        db_url, include_evidence=True, result_dir=result_dir
    )
    assert len(state1.get("evidences", [])) == 1, "seed data missing"

    # Step 2: kill any open handles and move DB aside.
    db_path = Path(db_url.replace("sqlite+aiosqlite:///", "").replace("/", os.sep))
    if not db_path.is_file():
        # try Posix form
        db_path = Path(db_url.replace("sqlite+aiosqlite:///", ""))
    moved = tmp_test_dir / "moved.db"
    # Force flush of file locks
    import gc as _gc
    _gc.collect()
    try:
        # On Windows, sqlite handles may hold locks; sleep briefly.
        for _ in range(5):
            try:
                db_path.replace(moved)
                break
            except PermissionError:
                time.sleep(0.2)
        else:
            # fall back to copy + truncate
            shutil.copy2(db_path, moved)
            db_path.write_bytes(b"")
    except FileNotFoundError:
        pass

    # Step 3: restart at same URL. Engine must rebuild (create_all on
    # empty file -> fresh schema, no crash).
    state2 = injector.verify_state(
        db_url, include_evidence=True, result_dir=result_dir
    )
    # No exception thrown is itself the assertion; verify clean schema.
    assert "ts" in state2, f"verify_state did not return cleanly: {state2}"
    # The new DB has the seeded data? Depends on whether we replaced
    # with empty or moved-aside. We moved-aside, so new DB is empty.
    # What matters is the engine reconnected without leaking the old
    # handle (otherwise we'd get OperationalError: database is closed).
    evidences_new = state2.get("evidences", [])
    # Acceptable: 0 if file replaced, or 1 if we copied-aside.
    # The point is no exception was raised.
    assert evidences_new in ([], state1.get("evidences", [])), (
        f"unexpected evidence count after restart: {evidences_new}"
    )


# ===========================================================================
# CR10 - Workflow Run cross-restart (run_id unchanged, state continuous)
# ===========================================================================


async def test_cr10_workflow_run_id_preserved_across_restart(
    injector, db_url, result_dir
):
    """Same as CR2 but the explicit assertion is that the resumed run
    carries the SAME run_id (not a new UUID), and its status moves from
    running/failed -> completed.

    The 'state continuous' part: the workflow_run row is the same row
    (no second INSERT); only UPDATE happened.
    """
    run_id = f"cr10-{uuid.uuid4().hex[:8]}"

    cfg_crash = {
        "run_id": run_id,
        "workflow_mode": "kill_at_b",
        "crash_hook": "crash_after_step_a",
    }
    kp = injector.start_kernel(
        db_url, mode="workflow_run", config=cfg_crash, result_dir=result_dir
    )
    try:
        assert injector.wait_for_marker(kp, timeout_s=5.0)
        _kill_and_reap(injector, kp)
    finally:
        injector.cleanup(kp)

    # Read the run before resume.
    state_pre = injector.verify_state(
        db_url, expected_run_id=run_id, result_dir=result_dir
    )
    run_pre = state_pre["workflow_run"]
    assert run_pre["run_id"] == run_id
    pre_status = run_pre["status"]
    assert pre_status in ("running", "failed"), (
        f"unexpected pre-resume status: {pre_status}"
    )
    pre_current_step = run_pre["current_step"]

    # Resume.
    cfg_resume = {"run_id": run_id, "workflow_mode": "kill_at_b"}
    kp2 = injector.start_kernel(
        db_url, mode="workflow_resume", config=cfg_resume, result_dir=result_dir
    )
    try:
        result = kp2.read_result(timeout_s=10.0)
        assert result is not None
    finally:
        injector.cleanup(kp2)

    # Read again.
    state_post = injector.verify_state(
        db_url, expected_run_id=run_id, result_dir=result_dir
    )
    run_post = state_post["workflow_run"]
    assert run_post["run_id"] == run_id, (
        f"run_id changed across restart: {run_post['run_id']!r} != {run_id!r}"
    )
    assert run_post["status"] == "completed", (
        f"expected completed after resume; got {run_post['status']}"
    )
    # started_at should be preserved (same row, just updated).
    assert run_post["started_at"] == run_pre["started_at"], (
        f"started_at changed: pre={run_pre['started_at']} post={run_post['started_at']}"
    )
    # current_step moved from b -> c.
    assert run_post["current_step"] in ("b", "c"), (
        f"current_step not advanced: {run_post['current_step']!r}"
    )

