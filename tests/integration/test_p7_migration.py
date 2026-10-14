"""P7 additive Alembic migration smoke test on isolated SQLite.

Must not delete P7 history. Real PostgreSQL upgrade still pending.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _load_migration():
    file = (
        Path(__file__).resolve().parents[2]
        / "scripts/persistence/migrations/versions"
        / "004_p7_workflow_execution_fencing.py"
    )
    spec = importlib.util.spec_from_file_location("p7_migration_004", file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_p7_migration_is_additive_and_repeat_safe(tmp_path):
    migration = _load_migration()
    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'migration.db').as_posix()}")
    try:
        with engine.begin() as conn:
            migration.op = Operations(MigrationContext.configure(conn))
            migration.upgrade()
            insp = sa.inspect(conn)
            assert {"workflow_effects", "workflow_leases"}.issubset(
                set(insp.get_table_names())
            )

            # Seed a record and repeat the migration: no drop or overwrite.
            conn.execute(
                sa.text(
                    "INSERT INTO workflow_effects "
                    "(effect_key, run_id, step_id, request_hash, status, receipt_json) "
                    "VALUES ('k', 'run', 'step', 'hash', 'uncertain', '{}')"
                )
            )
            migration.upgrade()
            rows = conn.execute(
                sa.text("SELECT status FROM workflow_effects WHERE effect_key='k'")
            ).all()
            assert rows == [("uncertain",)]
    finally:
        engine.dispose()


def test_p7_rollback_refuses_to_discard_execution_evidence(tmp_path):
    migration = _load_migration()
    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'preserve.db').as_posix()}")
    try:
        with engine.begin() as conn:
            migration.op = Operations(MigrationContext.configure(conn))
            migration.upgrade()
            conn.execute(sa.text(
                "INSERT INTO workflow_effects "
                "(effect_key, run_id, step_id, request_hash, status, receipt_json) "
                "VALUES ('sent-key','r','s','h','sent','{}')"
            ))
            with pytest.raises(RuntimeError, match="automatic table deletion"):
                migration.downgrade()
            assert "workflow_effects" in sa.inspect(conn).get_table_names()
    finally:
        engine.dispose()


def test_p7_empty_tables_allow_reversible_migration(tmp_path):
    migration = _load_migration()
    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    try:
        with engine.begin() as conn:
            migration.op = Operations(MigrationContext.configure(conn))
            migration.upgrade()
            migration.downgrade()
            tables = set(sa.inspect(conn).get_table_names())
            assert "workflow_effects" not in tables
            assert "workflow_leases" not in tables
    finally:
        engine.dispose()
