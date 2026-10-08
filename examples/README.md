# AIOS Kernel — Examples

Runnable demos for the AIOS Kernel Phase A scaffold. All examples use
SQLite in dev mode (no PG required) and can be invoked directly from the
repo root.

## three_step_workflow.py

End-to-end demo of `PGCheckpointerEngine` with a 3-step linear DAG:

    fetch -> transform -> write

- Each step is a plain async function wrapped via `from_callable`.
- The DAG is wired with `depends_on=[...]`.
- Outputs thread through via `ctx.metadata["prev_outputs"][<dep_id>]`.
- The example also exercises `engine.query()` for `status` and `history`
  and `engine.signal()` for a non-cancel `custom:ping` signal.

Run:

```
cd D:\AIOS\kernel
set PYTHONPATH=src
python examples/three_step_workflow.py
```

Override the database URL with `AIOS_WORKFLOW_DB`:

```
set AIOS_WORKFLOW_DB=postgresql+asyncpg://user:pw@localhost:5432/aios
python examples/three_step_workflow.py
```

(The default in this scaffold is `sqlite+aiosqlite:///./three_step_workflow.db`
which is auto-cleaned after the run.)

## Production note

The same code path works on PostgreSQL by switching the URL to
`postgresql+asyncpg://...` and running `Alembic` migrations (T0032) to
create the 3 tables (`workflow_runs`, `workflow_checkpoints`,
`activity_history`).
