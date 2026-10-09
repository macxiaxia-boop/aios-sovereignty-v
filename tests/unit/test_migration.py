"""test_migration.py - alembic up/down full cycle (T0032 deliverable)."""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

KERNEL_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = KERNEL_ROOT / "alembic.ini"


def _run_alembic(args, url):
    env = os.environ.copy()
    env["AIOS_KERNEL_DATABASE_URL"] = url
    cmd = [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args]
    result = subprocess.run(
        cmd,
        cwd=str(KERNEL_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    return result


@pytest.fixture
def sqlite_url(tmp_path):
    db_path = tmp_path / "test.db"
    yield f"sqlite+aiosqlite:///{db_path}"
    if db_path.exists():
        db_path.unlink()


def _tables_in(url):
    path = url.replace("sqlite+aiosqlite:///", "")
    con = sqlite3.connect(path)
    cur = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    names = [r[0] for r in cur.fetchall()]
    con.close()
    return names


# 1. upgrade head creates all 8 tables + alembic_version
def test_upgrade_head_creates_all_tables(sqlite_url):
    result = _run_alembic(["upgrade", "head"], sqlite_url)
    assert result.returncode == 0, f"alembic upgrade failed: {result.stderr}"
    tables = _tables_in(sqlite_url)
    expected = {
        "goals", "tasks", "plans", "artifacts", "evidences", "traces",
        "worker_runs", "verifier_runs", "alembic_version",
    }
    assert expected.issubset(set(tables)), f"missing tables: {expected - set(tables)}"


# 2. downgrade base (all the way to 001) removes all 8 tables
# Note: downgrade -1 from 003 only goes to 002, which drops decision_audit but
# leaves goals/tasks/etc. Use downgrade base to reach 001, which drops goals.
def test_downgrade_minus_one_removes_tables(sqlite_url):
    r1 = _run_alembic(["upgrade", "head"], sqlite_url)
    assert r1.returncode == 0
    r2 = _run_alembic(["downgrade", "base"], sqlite_url)
    assert r2.returncode == 0, f"alembic downgrade failed: {r2.stderr}"
    tables = _tables_in(sqlite_url)
    assert "goals" not in tables
    assert "tasks" not in tables
    assert "plans" not in tables
    assert "artifacts" not in tables
    assert "evidences" not in tables
    assert "traces" not in tables
    assert "worker_runs" not in tables
    assert "verifier_runs" not in tables
    assert "alembic_version" in tables


# 3. upgrade twice is idempotent
def test_double_upgrade_is_idempotent(sqlite_url):
    r1 = _run_alembic(["upgrade", "head"], sqlite_url)
    r2 = _run_alembic(["upgrade", "head"], sqlite_url)
    assert r1.returncode == 0
    assert r2.returncode == 0


# 4. Round-trip: upgrade, downgrade, upgrade again
def test_upgrade_downgrade_upgrade_roundtrip(sqlite_url):
    _run_alembic(["upgrade", "head"], sqlite_url)
    _run_alembic(["downgrade", "-1"], sqlite_url)
    r = _run_alembic(["upgrade", "head"], sqlite_url)
    assert r.returncode == 0
    tables = _tables_in(sqlite_url)
    assert "goals" in tables
    assert "tasks" in tables


# 5. current revision is 003 (head)
def test_current_revision_is_003(sqlite_url):
    _run_alembic(["upgrade", "head"], sqlite_url)
    result = _run_alembic(["current"], sqlite_url)
    assert result.returncode == 0
    assert "003" in result.stdout


# 6. ORM can read alembic-created schema
@pytest.mark.asyncio
async def test_orm_can_read_migrated_schema(sqlite_url):
    _run_alembic(["upgrade", "head"], sqlite_url)
    from aios_kernel.domain.services.repository import make_engine
    from sqlalchemy import text as sa_text
    engine = make_engine(sqlite_url)
    async with engine.connect() as conn:
        for table in ("goals", "tasks", "plans", "artifacts", "evidences", "traces",
                      "worker_runs", "verifier_runs"):
            r = await conn.execute(sa_text(f"SELECT COUNT(*) FROM {table}"))
            count = r.scalar()
            assert count == 0
    await engine.dispose()


