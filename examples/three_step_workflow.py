"""three_step_workflow.py - 3-Activity serial example for AIOS Kernel T0033.

Run:
    cd D:\\AIOS\\kernel
    set PYTHONPATH=src
    python examples/three_step_workflow.py

Output: prints WorkflowRun + per-step history.

This is the smoke example that demonstrates:
  - WorkflowEngine Protocol
  - 3 sequential WorkflowSteps with depends_on forming a linear DAG
  - PG checkpointer (sqlite dev / PG prod)
  - step-level checkpoints
  - activity history
  - engine.query() for "status" and "history"
  - dependency output threading via ctx.metadata["prev_outputs"][<dep_id>]
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Allow `python examples/three_step_workflow.py` from repo root
_KERNEL_ROOT = Path(__file__).resolve().parents[1]
if str(_KERNEL_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_KERNEL_ROOT / "src"))

from aios_kernel.workflows import (  # noqa: E402
    ActivityContext,
    ActivityResult,
    PGCheckpointerEngine,
    Query,
    Signal,
    StepMeta,
    Workflow,
    WorkflowStep,
    from_callable,
)

# ---------- The 3 activities -----------------------------------------------


async def fetch_data(ctx: ActivityContext) -> ActivityResult:
    """Step 1: pretend to fetch data from an external API."""
    print(f"  [fetch_data] attempt={ctx.attempt}  -> 42 records")
    return ActivityResult(
        success=True,
        output={"records": [{"id": i, "value": i * 7} for i in range(42)]},
    )


async def transform_data(ctx: ActivityContext) -> ActivityResult:
    """Step 2: pretend to transform the data.

    Reads its input from ctx.metadata["prev_outputs"]["fetch"] (the output
    of the upstream `fetch` step).
    """
    prev = ctx.metadata.get("prev_outputs", {}).get("fetch", {})
    records = prev.get("records", [])
    print(f"  [transform_data] attempt={ctx.attempt}  -> normalized {len(records)} records")
    return ActivityResult(
        success=True,
        output={"normalized": [{"id": r["id"], "v2": r["value"]} for r in records]},
    )


async def write_data(ctx: ActivityContext) -> ActivityResult:
    """Step 3: pretend to write to a destination.

    Reads its input from ctx.metadata["prev_outputs"]["transform"].
    """
    prev = ctx.metadata.get("prev_outputs", {}).get("transform", {})
    n = len(prev.get("normalized", []))
    print(f"  [write_data] attempt={ctx.attempt}  -> wrote {n} records")
    return ActivityResult(success=True, output={"wrote": n})


# ---------- Wire up the workflow --------------------------------------------


def build_workflow() -> Workflow:
    return Workflow(
        id="three-step-demo",
        name="Three Step Workflow (fetch -> transform -> write)",
        description="T0033 example: linear 3-step DAG with PG checkpointer",
        steps=[
            WorkflowStep(
                meta=StepMeta(id="fetch", name="Fetch Data"),
                activity=from_callable("fetch_data", fetch_data),
                depends_on=[],
            ),
            WorkflowStep(
                meta=StepMeta(id="transform", name="Transform Data"),
                activity=from_callable("transform_data", transform_data),
                depends_on=["fetch"],
            ),
            WorkflowStep(
                meta=StepMeta(id="write", name="Write Data"),
                activity=from_callable("write_data", write_data),
                depends_on=["transform"],
            ),
        ],
    )


# ---------- Main ------------------------------------------------------------


async def main() -> int:
    db_url = os.environ.get(
        "AIOS_WORKFLOW_DB",
        "sqlite+aiosqlite:///./three_step_workflow.db",
    )
    print("== three_step_workflow ==")
    print(f"  db = {db_url}")
    print("  workflow = three-step-demo")
    print()

    # If a previous run left a file behind, clean it up BEFORE we open it.
    if db_url.startswith("sqlite") and ":memory:" not in db_url:
        try:
            os.remove(db_url.split("///", 1)[1])
        except FileNotFoundError:
            pass

    wf = build_workflow()
    print(f"Workflow id: {wf.id}")
    print("Steps in topological order:")
    for s in wf.topological_order():
        print(f"  - {s.id}  ({s.name})  depends_on={s.depends_on}")
    print()

    engine = PGCheckpointerEngine(db_url)
    await engine.init()

    try:
        run = await engine.start(wf, input={"source": "demo", "limit": 42})
        print()
        print("== run finished ==")
        print(f"  run_id     = {run.run_id}")
        print(f"  status     = {run.status.value}")
        print(f"  current    = {run.current_step}")
        print(f"  error      = {run.error}")
        print(f"  started_at = {run.started_at}")
        print(f"  completed  = {run.completed_at}")

        # Demonstrate the query() method
        history = await engine.query(run.run_id, Query(type="history"))
        print()
        print("== checkpoint history ==")
        for cp in history:
            print(
                f"  - step={cp['step_id']:<10s} "
                f"index={cp['step_index']} "
                f"status={cp['status']} "
                f"attempt={cp['attempt']}"
            )

        # Demonstrate get_status()
        st = await engine.get_status(run.run_id)
        print()
        print(f"== engine.get_status -> {st.value}")

        # Demonstrate signal() (non-cancel type, just stored)
        await engine.signal(run.run_id, Signal(type="custom:ping", payload={"msg": "hi"}))
        st_after_signal = await engine.query(run.run_id, Query(type="status"))
        print(f"== after custom signal, status still = {st_after_signal.value}")

    finally:
        await engine.close()
        if db_url.startswith("sqlite") and ":memory:" not in db_url:
            try:
                os.remove(db_url.split("///", 1)[1])
            except FileNotFoundError:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
