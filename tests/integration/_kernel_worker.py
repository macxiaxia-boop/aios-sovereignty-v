"""_kernel_worker.py — Kernel subprocess for T0037 crash recovery tests.

Spawned by tests/integration/crash_injector.py. Runs one operation
(workflow / goal / plan / verifier / evidence) against a SQLite DB,
optionally injecting a crash at a configured point, and writes a
JSON result to --result-path before exiting.

Usage:
    python _kernel_worker.py \
        --db-url sqlite+aiosqlite:///path/to.db \
        --mode MODE \
        --config JSON_CONFIG \
        --result-path path/to/result.json

Modes:
    goal_create        Create a goal (with optional crash_before_commit hook)
    workflow_run       Run a workflow (3-step DAG; crash_after_step_a / etc.)
    plan_revert        Plan version bump (crash_after_old_inactive / etc.)
    verifier_call      Sign an evidence (crash_after_record / etc.)
    budget_check       Deduct from goal budget (crash_before_commit)
    evidence_write     Atomic evidence write (crash_before_final_commit)
    verifier_daemon    Independent verifier heartbeat (CR8 background process)
    verify_state       Read DB state to JSON (used after crash)
    workflow_resume    Resume a workflow run from latest checkpoint

Crash hooks (config["crash_hook"]):
    "none"                   No crash — run to completion
    "crash_after_step_a"     Workflow: kill after step a checkpoint, before step b
    "crash_at_step_b"        Workflow: kill mid-step-b (uncaught exception path)
    "crash_before_commit"    Service-level: kill right before session.commit()
    "crash_after_old_inactive" Plan reversion: after mark_inactive, before new add
    "crash_after_record"     Verifier: after row add, before commit
    "crash_mid_deduct"       Budget: between debit and commit
    "crash_before_final_commit" Evidence: after row add, before final commit

The worker never catches the crash hook — it relies on the parent
calling kill_n9 / kill_terminate. The hook writes a marker file (so
the parent knows we reached the hook point) then sleeps forever.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Ensure src/ is on sys.path so the worker can import aios_kernel.
_THIS = Path(__file__).resolve()
_KERNEL_ROOT = _THIS.parent.parent.parent  # tests/integration/_kernel_worker.py -> kernel/
_SRC = _KERNEL_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ---------- helpers ---------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _write_result(path, payload):
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, default=str), encoding="utf-8")


def _maybe_crash(hook, expected, marker_path=None):
    """If hook == expected, write a marker file (so parent knows we reached
    the hook) then sleep forever (parent will taskkill us)."""
    if hook != expected:
        return
    if marker_path:
        Path(marker_path).parent.mkdir(parents=True, exist_ok=True)
        Path(marker_path).write_text(_now_iso(), encoding="utf-8")
    # Sleep forever — parent will kill us. Never returns.
    while True:
        time.sleep(0.5)


# ---------- mode: goal_create ----------------------------------------------


async def _goal_create(db_url, config, result_path):
    from aios_kernel.domain.services.repository import (
        make_engine,
        make_session_factory,
        session_scope,
    )
    from aios_kernel.domain.services.goal_service import GoalService
    from aios_kernel.persistence.repository import SqlAlchemyRepository
    from aios_kernel.persistence import create_all

    engine = make_engine(db_url)
    try:
        await create_all(engine)
        factory = make_session_factory(engine)
        crash_hook = config.get("crash_hook", "none")
        if crash_hook == "crash_before_commit":
            # Open a session, add the goal, write marker, sleep (parent kills us).
            # We do NOT use session_scope (which would commit). Instead, use
            # a manual session so the goal remains uncommitted until we exit.
            async with factory() as session:
                repo = SqlAlchemyRepository(session)
                from aios_kernel.domain.goal import Goal
                g = Goal(
                    title=config["title"],
                    success_criteria=config["success_criteria"],
                    budget=config["budget"],
                    owner=config["owner"],
                    description=config.get("description"),
                )
                await repo.add(g)
                await session.flush()
                # Write marker then sleep — parent kills us BEFORE session commit
                _maybe_crash("crash_before_commit", "crash_before_commit",
                             marker_path=config.get("marker_path"))
                # If we get here, parent didn't kill us in time — explicit fail
                raise RuntimeError("worker survived crash hook — bug")

        # Normal path: full create + commit
        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            svc = GoalService(repo)
            g = await svc.create_goal(
                title=config["title"],
                success_criteria=config["success_criteria"],
                budget=config["budget"],
                owner=config["owner"],
                description=config.get("description"),
            )
            return {"goal_id": g.id, "status": g.status.value, "ts": _now_iso()}
    finally:
        await engine.dispose()


# ---------- mode: workflow_run ---------------------------------------------


async def _workflow_run(db_url, config, result_path):
    from aios_kernel.workflows import (
        PGCheckpointerEngine,
        RetryPolicy,
        StepMeta,
        Workflow,
        WorkflowStep,
        ActivityResult,
        from_callable,
    )

    engine = PGCheckpointerEngine(db_url)
    try:
        await engine.init()
        crash_hook = config.get("crash_hook", "none")
        run_id = config["run_id"]
        mode = config.get("workflow_mode", "kill_at_b")

        if mode == "kill_at_b":
            async def step_a(ctx):
                return ActivityResult(success=True, output={"a": 1, "attempt": ctx.attempt})

            async def step_b(ctx):
                if crash_hook == "crash_after_step_a":
                    _maybe_crash(
                        "crash_after_step_a",
                        "crash_after_step_a",
                        marker_path=config.get("marker_path"),
                    )
                # If hook didn't kill us, raise to fail the run (for cleanup)
                raise RuntimeError("simulated crash in step b")

            async def step_c(ctx):
                return ActivityResult(success=True, output={"c": 3})

            steps = [
                WorkflowStep(
                    meta=StepMeta(id="a", name="A"),
                    activity=from_callable("a", step_a),
                ),
                WorkflowStep(
                    meta=StepMeta(id="b", name="B"),
                    activity=from_callable("b", step_b),
                    depends_on=["a"],
                    retry_policy=RetryPolicy(
                        max_attempts=1, initial_delay_s=0.0, max_delay_s=0.0
                    ),
                ),
                WorkflowStep(
                    meta=StepMeta(id="c", name="C"),
                    activity=from_callable("c", step_c),
                    depends_on=["b"],
                ),
            ]
        elif mode == "success_3step":
            async def step_a(ctx):
                return ActivityResult(success=True, output={"a": 1, "attempt": ctx.attempt})

            async def step_b(ctx):
                return ActivityResult(success=True, output={"b": 2})

            async def step_c(ctx):
                return ActivityResult(success=True, output={"c": 3})

            steps = [
                WorkflowStep(
                    meta=StepMeta(id="a", name="A"),
                    activity=from_callable("a", step_a),
                ),
                WorkflowStep(
                    meta=StepMeta(id="b", name="B"),
                    activity=from_callable("b", step_b),
                    depends_on=["a"],
                ),
                WorkflowStep(
                    meta=StepMeta(id="c", name="C"),
                    activity=from_callable("c", step_c),
                    depends_on=["b"],
                ),
            ]
        else:
            raise ValueError(f"unknown workflow_mode: {mode!r}")

        wf = Workflow(id=f"cr-wf-{mode}", name="crash recovery", steps=steps)
        try:
            run = await engine.start(wf, run_id=run_id)
            return {
                "run_id": run.run_id,
                "status": run.status.value,
                "current_step": run.current_step,
                "ts": _now_iso(),
            }
        except Exception as exc:
            return {
                "run_id": run_id,
                "status": "exception",
                "error": f"{type(exc).__name__}: {exc}",
                "ts": _now_iso(),
            }
    finally:
        await engine.close()


# ---------- mode: plan_revert ----------------------------------------------


async def _plan_revert(db_url, config, result_path):
    from aios_kernel.domain.plan import DependencyKind, PlanStep, StepType
    from aios_kernel.domain.services.goal_service import GoalService
    from aios_kernel.domain.services.plan_service import PlanService
    from aios_kernel.domain.services.repository import (
        make_engine,
        make_session_factory,
        session_scope,
    )
    from aios_kernel.persistence import create_all
    from aios_kernel.persistence.repository import SqlAlchemyRepository

    engine = make_engine(db_url)
    try:
        await create_all(engine)
        factory = make_session_factory(engine)
        crash_hook = config.get("crash_hook", "none")

        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            goal_svc = GoalService(repo)
            plan_svc = PlanService(repo)
            g = await goal_svc.create_goal(
                title=config["goal_title"],
                success_criteria="crash recovery test",
                budget=100.0,
                owner="crash-test",
            )
            v1_steps = [
                PlanStep(plan_id="placeholder", name="s1", kind=StepType.TASK, order=0),
                PlanStep(plan_id="placeholder", name="s2", kind=StepType.TASK, order=1),
            ]
            v1 = await plan_svc.create_plan(
                goal_id=g.id,
                steps=v1_steps,
                title="v1",
                created_by="crash-test",
            )

        if crash_hook == "crash_after_old_inactive":
            async with factory() as session:
                repo = SqlAlchemyRepository(session)
                plan_svc2 = PlanService(repo)
                from sqlalchemy import select
                from aios_kernel.persistence.models import PlanORM
                from aios_kernel.domain.plan import Plan as PydPlan

                row = (
                    await session.execute(
                        select(PlanORM).where(PlanORM.id == v1.id)
                    )
                ).scalar_one()
                pyd_v1 = PydPlan.model_validate(row.envelope_json)
                pyd_v1.mark_inactive()
                await repo.add(pyd_v1)
                # Sleep BEFORE commit — parent kills us
                _maybe_crash(
                    "crash_after_old_inactive",
                    "crash_after_old_inactive",
                    marker_path=config.get("marker_path"),
                )
                raise RuntimeError("worker survived crash hook")

        # Normal path: full reversion
        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            plan_svc3 = PlanService(repo)
            from sqlalchemy import select
            from aios_kernel.persistence.models import PlanORM
            from aios_kernel.domain.plan import Plan as PydPlan

            row = (
                await session.execute(
                    select(PlanORM).where(PlanORM.id == v1.id)
                )
            ).scalar_one()
            pyd_v1 = PydPlan.model_validate(row.envelope_json)
            new_steps = [
                PlanStep(plan_id="placeholder", name="s1", kind=StepType.TASK, order=0),
                PlanStep(plan_id="placeholder", name="s2", kind=StepType.TASK, order=1),
                PlanStep(plan_id="placeholder", name="s3", kind=StepType.TASK, order=2),
            ]
            new_plan = await plan_svc3.create_version(
                pyd_v1, steps=new_steps, title="v2", created_by="crash-test"
            )
            return {
                "goal_id": g.id,
                "v1_id": v1.id,
                "v2_id": new_plan.id,
                "v2_version": new_plan.version,
                "ts": _now_iso(),
            }
    finally:
        await engine.dispose()


# ---------- mode: verifier_call --------------------------------------------


async def _verifier_call(db_url, config, result_path):
    from aios_kernel.domain.evidence import Evidence, Verdict
    from aios_kernel.domain.services.goal_service import GoalService
    from aios_kernel.domain.services.repository import (
        make_engine,
        make_session_factory,
        session_scope,
    )
    from aios_kernel.domain.services.task_service import TaskService, TaskStatus
    from aios_kernel.persistence import create_all
    from aios_kernel.persistence.repository import SqlAlchemyRepository

    engine = make_engine(db_url)
    try:
        await create_all(engine)
        factory = make_session_factory(engine)
        crash_hook = config.get("crash_hook", "none")

        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            goal_svc = GoalService(repo)
            task_svc = TaskService(repo)
            g = await goal_svc.create_goal(
                title="verifier-crash-test",
                success_criteria="x",
                budget=10.0,
                owner="crash-test",
            )
            t = await task_svc.create_task(
                goal_id=g.id, title="t1", task_type="custom"
            )
            await task_svc.transition(t, TaskStatus.RUNNING)
            await task_svc.transition(t, TaskStatus.VERIFYING)
            task_id = t.id

        if crash_hook == "crash_after_record":
            async with factory() as session:
                repo = SqlAlchemyRepository(session)
                ev = Evidence(
                    task_id=task_id,
                    artifact_ids=[],
                    verifier_id="test-verifier",
                    verdict=Verdict.PASS,
                    details={"checks": ["all"]},
                )
                await repo.add(ev)
                _maybe_crash(
                    "crash_after_record",
                    "crash_after_record",
                    marker_path=config.get("marker_path"),
                )
                raise RuntimeError("worker survived crash hook")

        # Normal path
        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            ev = Evidence(
                task_id=task_id,
                artifact_ids=[],
                verifier_id="test-verifier",
                verdict=Verdict.PASS,
                details={"checks": ["all"]},
                evidence_hash=hashlib.sha256(
                    f"{task_id}|test-verifier|PASS".encode()
                ).hexdigest(),
            )
            await repo.add(ev)
            return {"task_id": task_id, "evidence_id": ev.id, "ts": _now_iso()}
    finally:
        await engine.dispose()


# ---------- mode: budget_check ---------------------------------------------


async def _budget_check(db_url, config, result_path):
    from aios_kernel.domain.services.goal_service import GoalService
    from aios_kernel.domain.services.repository import (
        make_engine,
        make_session_factory,
        session_scope,
    )
    from aios_kernel.persistence import create_all
    from aios_kernel.persistence.repository import SqlAlchemyRepository

    engine = make_engine(db_url)
    try:
        await create_all(engine)
        factory = make_session_factory(engine)
        crash_hook = config.get("crash_hook", "none")

        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            goal_svc = GoalService(repo)
            g = await goal_svc.create_goal(
                title="budget-crash-test",
                success_criteria="x",
                budget=config["initial_budget"],
                owner="crash-test",
            )
            initial_budget = g.budget
            goal_id = g.id

        if crash_hook == "crash_mid_deduct":
            async with factory() as session:
                repo = SqlAlchemyRepository(session)
                from sqlalchemy import select
                from aios_kernel.persistence.models import GoalORM
                from aios_kernel.domain.goal import Goal as PydGoal

                row = (
                    await session.execute(
                        select(GoalORM).where(GoalORM.id == goal_id)
                    )
                ).scalar_one()
                pyd_g = PydGoal.model_validate(row.envelope_json)
                pyd_g.metadata["spent"] = config["deduct_amount"]
                pyd_g.touch()
                await repo.add(pyd_g)
                _maybe_crash(
                    "crash_mid_deduct",
                    "crash_mid_deduct",
                    marker_path=config.get("marker_path"),
                )
                raise RuntimeError("worker survived crash hook")

        # Normal path: full commit
        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            from sqlalchemy import select
            from aios_kernel.persistence.models import GoalORM
            from aios_kernel.domain.goal import Goal as PydGoal

            row = (
                await session.execute(
                    select(GoalORM).where(GoalORM.id == goal_id)
                )
            ).scalar_one()
            pyd_g = PydGoal.model_validate(row.envelope_json)
            pyd_g.metadata["spent"] = config["deduct_amount"]
            pyd_g.touch()
            await repo.add(pyd_g)
            return {
                "goal_id": goal_id,
                "initial_budget": initial_budget,
                "spent": config["deduct_amount"],
                "ts": _now_iso(),
            }
    finally:
        await engine.dispose()


# ---------- mode: evidence_write -------------------------------------------


async def _evidence_write(db_url, config, result_path):
    """Test atomicity: write evidence + task update in one transaction."""
    from aios_kernel.domain.evidence import Evidence, Verdict
    from aios_kernel.domain.services.goal_service import GoalService
    from aios_kernel.domain.services.repository import (
        make_engine,
        make_session_factory,
        session_scope,
    )
    from aios_kernel.domain.services.task_service import TaskService, TaskStatus
    from aios_kernel.persistence import create_all
    from aios_kernel.persistence.repository import SqlAlchemyRepository

    engine = make_engine(db_url)
    try:
        await create_all(engine)
        factory = make_session_factory(engine)
        crash_hook = config.get("crash_hook", "none")

        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            goal_svc = GoalService(repo)
            task_svc = TaskService(repo)
            g = await goal_svc.create_goal(
                title="evidence-write-test",
                success_criteria="x",
                budget=10.0,
                owner="crash-test",
            )
            t = await task_svc.create_task(
                goal_id=g.id, title="t1", task_type="custom"
            )
            task_id = t.id

        if crash_hook == "crash_before_final_commit":
            async with factory() as session:
                repo = SqlAlchemyRepository(session)
                ev = Evidence(
                    task_id=task_id,
                    artifact_ids=[],
                    verifier_id="test-verifier",
                    verdict=Verdict.PASS,
                    details={"k": "v"},
                )
                await repo.add(ev)
                await session.flush()
                _maybe_crash(
                    "crash_before_final_commit",
                    "crash_before_final_commit",
                    marker_path=config.get("marker_path"),
                )
                raise RuntimeError("worker survived crash hook")

        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            ev = Evidence(
                task_id=task_id,
                artifact_ids=[],
                verifier_id="test-verifier",
                verdict=Verdict.PASS,
                details={"k": "v"},
                evidence_hash=hashlib.sha256(
                    f"{task_id}|test-verifier|PASS|v2".encode()
                ).hexdigest(),
            )
            await repo.add(ev)
            return {"task_id": task_id, "evidence_id": ev.id, "ts": _now_iso()}
    finally:
        await engine.dispose()


# ---------- mode: verifier_daemon (CR8 background process) ----------------


async def _verifier_daemon(db_url, config, result_path):
    """Long-running daemon that periodically writes heartbeat evidence."""
    from aios_kernel.domain.evidence import Evidence, Verdict
    from aios_kernel.domain.services.goal_service import GoalService
    from aios_kernel.domain.services.repository import (
        make_engine,
        make_session_factory,
        session_scope,
    )
    from aios_kernel.persistence import create_all
    from aios_kernel.persistence.repository import SqlAlchemyRepository

    # Popen returns the launcher PID (e.g. python.exe wrapper), not the actual
    # Python interpreter PID. Capture the parent PID (= launcher = Popen pid)
    # so it matches what injector.start_kernel recorded as daemon_kp.pid.
    pid = os.getppid()
    heartbeat_count = 0

    engine = make_engine(db_url)
    try:
        await create_all(engine)
        factory = make_session_factory(engine)

        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            goal_svc = GoalService(repo)
            g = await goal_svc.create_goal(
                title="verifier-daemon-test",
                success_criteria="x",
                budget=10.0,
                owner="crash-test",
            )
            task_id = config.get("task_id") or g.id

        duration_s = float(config.get("duration_s", 5.0))
        deadline = time.time() + duration_s
        while time.time() < deadline:
            async with session_scope(factory) as session:
                repo = SqlAlchemyRepository(session)
                ev = Evidence(
                    task_id=task_id,
                    artifact_ids=[],
                    verifier_id=f"daemon-{pid}",
                    verdict=Verdict.PASS,
                    details={"heartbeat": heartbeat_count},
                )
                await repo.add(ev)
            heartbeat_count += 1
            time.sleep(0.2)

        return {
            "daemon_pid": pid,
            "task_id": task_id,
            "heartbeat_count": heartbeat_count,
            "ts": _now_iso(),
        }
    finally:
        await engine.dispose()


# ---------- mode: verify_state --------------------------------------------


async def _verify_state(db_url, config, result_path):
    """Read state from DB and dump to result."""
    from aios_kernel.workflows.persistence import (
        WorkflowRunRow,
        WorkflowCheckpointRow,
        ActivityHistoryRow,
        make_engine,
        make_session_factory,
    )
    from aios_kernel.persistence.models import GoalORM, PlanORM, EvidenceORM, TaskORM
    from sqlalchemy import select, or_

    engine = make_engine(db_url)
    try:
        # R1347: ensure all tables exist (workflow + kernel persistence) so
        # verify_state works on fresh DB without prior worker run.
        from aios_kernel.workflows import init_schema as _init_wf_schema
        from aios_kernel.persistence import create_all as _create_all_kernel
        await _init_wf_schema(engine)
        await _create_all_kernel(engine)
        factory = make_session_factory(engine)
        result = {"ts": _now_iso()}

        async with factory() as session:
            run_id = config.get("run_id")
            # R1347: always populate workflow_run with at least run_id + status='missing'
            # so tests that do state["workflow_run"]["run_id"] never KeyError
            if run_id:
                run_row = await session.get(WorkflowRunRow, run_id)
                if run_row:
                    result["workflow_run"] = {
                        "run_id": run_row.run_id,
                        "workflow_id": run_row.workflow_id,
                        "status": run_row.status,
                        "current_step": run_row.current_step,
                        "error": run_row.error,
                        "started_at": run_row.started_at.isoformat()
                            if run_row.started_at else None,
                        "completed_at": run_row.completed_at.isoformat()
                            if run_row.completed_at else None,
                    }
                else:
                    # R1347: row not found (engine race / DB hit timing) — populate stub
                    result["workflow_run"] = {
                        "run_id": run_id,
                        "workflow_id": None,
                        "status": "missing",
                        "current_step": None,
                        "error": "row not found in DB at verify_state time",
                        "started_at": None,
                        "completed_at": None,
                    }
            else:
                # R1347: no run_id requested → empty stub
                result["workflow_run"] = {}

            # R1347: cp_rows + hist_rows belong to the if-run_id branch,
            # not the inner if run_row branch. Move out + reindent.
            if run_id and result["workflow_run"].get("status") != "missing":
                cp_rows = (
                    await session.execute(
                        select(WorkflowCheckpointRow).where(
                            WorkflowCheckpointRow.run_id == run_id
                        ).order_by(WorkflowCheckpointRow.step_index)
                    )
                ).scalars().all()
                result["checkpoints"] = [
                    {
                        "step_id": r.step_id,
                        "step_index": r.step_index,
                        "status": r.status,
                        "attempt": r.attempt,
                    }
                    for r in cp_rows
                ]
                hist_rows = (
                    await session.execute(
                        select(ActivityHistoryRow).where(
                            ActivityHistoryRow.run_id == run_id
                        ).order_by(ActivityHistoryRow.id)
                    )
                ).scalars().all()
                result["activity_history"] = [
                    {
                        "step_id": r.step_id,
                        "attempt": r.attempt,
                        "status": r.status,
                    }
                    for r in hist_rows
                ]

            if config.get("include_goals", True):
                goal_rows = (
                    await session.execute(select(GoalORM))
                ).scalars().all()
                result["goals"] = [
                    {
                        "id": g.id,
                        "title": g.title,
                        "status": g.status,
                        "budget": g.budget,
                        "metadata": g.metadata_,
                    }
                    for g in goal_rows
                ]

            if config.get("include_plans", False):
                plan_rows = (
                    await session.execute(select(PlanORM).order_by(PlanORM.version))
                ).scalars().all()
                result["plans"] = [
                    {
                        "id": p.id,
                        "goal_id": p.goal_id,
                        "version": p.version,
                        "is_active": p.is_active,
                    }
                    for p in plan_rows
                ]

            if config.get("include_evidence", False):
                ev_rows = (
                    await session.execute(select(EvidenceORM))
                ).scalars().all()
                evidence_list = [
                    {
                        "id": e.id,
                        "task_id": e.task_id,
                        "verifier_id": e.verifier_id,
                        "verdict": e.verdict,
                        "cost_yuan": e.cost_yuan,
                    }
                    for e in ev_rows
                ]
                # R1347 backward-compat aliases (tests expect "evidences")
                result["evidence"] = evidence_list
                result["evidences"] = evidence_list

            if config.get("include_daemon_heartbeats", False):
                daemon_rows = (
                    await session.execute(
                        select(EvidenceORM).where(
                            EvidenceORM.verifier_id.like("daemon-%")
                        ).order_by(EvidenceORM.created_at)
                    )
                ).scalars().all()
                result["daemon_heartbeats"] = [
                    {
                        "id": e.id,
                        "verifier_id": e.verifier_id,
                        "details": e.details,
                        "created_at": e.created_at.isoformat()
                            if e.created_at else None,
                    }
                    for e in daemon_rows
                ]

        return result
    finally:
        await engine.dispose()


# ---------- mode: workflow_resume ------------------------------------------


async def _workflow_resume(db_url, config, result_path):
    """Resume a workflow run from latest checkpoint. Used after crash to
    verify the workflow completes."""
    from aios_kernel.workflows import (
        PGCheckpointerEngine,
        RetryPolicy,
        StepMeta,
        Workflow,
        WorkflowStep,
        ActivityResult,
        from_callable,
    )

    engine = PGCheckpointerEngine(db_url)
    try:
        await engine.init()
        run_id = config["run_id"]
        mode = config.get("workflow_mode", "kill_at_b")

        if mode == "kill_at_b":
            async def step_a(ctx):
                return ActivityResult(success=True, output={"a": 1, "attempt": ctx.attempt})

            async def step_b(ctx):
                return ActivityResult(success=True, output={"b": 2})

            async def step_c(ctx):
                return ActivityResult(success=True, output={"c": 3})

            steps = [
                WorkflowStep(
                    meta=StepMeta(id="a", name="A"),
                    activity=from_callable("a", step_a),
                ),
                WorkflowStep(
                    meta=StepMeta(id="b", name="B"),
                    activity=from_callable("b", step_b),
                    depends_on=["a"],
                    retry_policy=RetryPolicy(
                        max_attempts=1, initial_delay_s=0.0, max_delay_s=0.0
                    ),
                ),
                WorkflowStep(
                    meta=StepMeta(id="c", name="C"),
                    activity=from_callable("c", step_c),
                    depends_on=["b"],
                ),
            ]
        else:
            raise ValueError(f"unknown workflow_mode for resume: {mode!r}")

        wf = Workflow(id=f"cr-wf-{mode}", name="crash recovery", steps=steps)
        try:
            run = await engine.resume(wf, run_id)
            return {
                "run_id": run.run_id,
                "status": run.status.value,
                "current_step": run.current_step,
                "ts": _now_iso(),
            }
        except Exception as exc:
            return {
                "run_id": run_id,
                "status": "exception",
                "error": f"{type(exc).__name__}: {exc}",
                "ts": _now_iso(),
            }
    finally:
        await engine.close()


# ---------- entry point ----------------------------------------------------


MODE_DISPATCH = {
    "goal_create": _goal_create,
    "workflow_run": _workflow_run,
    "plan_revert": _plan_revert,
    "verifier_call": _verifier_call,
    "budget_check": _budget_check,
    "evidence_write": _evidence_write,
    "verifier_daemon": _verifier_daemon,
    "verify_state": _verify_state,
    "workflow_resume": _workflow_resume,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--mode", required=True, choices=list(MODE_DISPATCH))
    parser.add_argument("--config", default="{}")
    parser.add_argument("--result-path", default=None)
    args = parser.parse_args()

    config = json.loads(args.config) if args.config else {}
    handler = MODE_DISPATCH[args.mode]

    try:
        result = asyncio.run(handler(args.db_url, config, args.result_path))
    except Exception as exc:
        result = {
            "mode": args.mode,
            "status": "worker_exception",
            "error": f"{type(exc).__name__}: {exc}",
            "ts": _now_iso(),
        }

    _write_result(args.result_path, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())

