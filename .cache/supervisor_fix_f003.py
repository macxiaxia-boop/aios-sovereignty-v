#!/usr/bin/env python3
"""Fix F003 test bugs as codex supervisor."""
import pathlib

# Fix 1: F003 alembic downgrade test - chain -1 twice to drop decision_audit
p = pathlib.Path(r"D:\AIOS\kernel\tests\unit\test_decision_audit.py")
src = p.read_text(encoding="utf-8")

old = '''def test_alembic_downgrade_002_drops_decision_audit_table(tmp_path):
    """alembic downgrade -1 (from head -> 001) drops the decision_audit table."""
    db_path = tmp_path / "f003.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    r1 = _run_alembic(["upgrade", "head"], url)
    assert r1.returncode == 0
    r2 = _run_alembic(["downgrade", "-1"], url)
    assert r2.returncode == 0, f"downgrade failed: {r2.stderr}"
    tables = _tables_in(url)
    assert "decision_audit" not in tables'''

new = '''def test_alembic_downgrade_002_drops_decision_audit_table(tmp_path):
    """alembic downgrade to 001 drops the decision_audit table added by 002.

    Phase F puts the head at 003 (after F001 goal_contract). -1 from head only
    goes to 002, which still has decision_audit. Chain two -1 to reach 001.
    """
    db_path = tmp_path / "f003.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    r1 = _run_alembic(["upgrade", "head"], url)
    assert r1.returncode == 0
    _run_alembic(["downgrade", "-1"], url)  # 003 -> 002
    r2 = _run_alembic(["downgrade", "-1"], url)  # 002 -> 001
    assert r2.returncode == 0, f"downgrade failed: {r2.stderr}"
    tables = _tables_in(url)
    assert "decision_audit" not in tables'''

assert old in src, "old F003 alembic block not found"
src = src.replace(old, new)

# Fix 2: F003 test_link_to_goal_fk_constraint — enable FK on SQLite per test
old_fk = '''@pytest.mark.asyncio
async def test_link_to_goal_fk_constraint(db_repo, async_engine):
    """Inserting an audit with a non-existent goal_id must fail at the FK."""
    from sqlalchemy.exc import IntegrityError

    svc = DecisionService(db_repo)
    # The commit inside record() flushes the INSERT; SQLite enforces the FK
    # at flush time, so the IntegrityError is raised synchronously here.
    with pytest.raises(IntegrityError):
        await svc.record(
            goal_id="does-not-exist",
            actor=DecisionActor.CODEX,
            rationale="r",
            chosen="c",
        )'''

new_fk = '''@pytest.mark.asyncio
async def test_link_to_goal_fk_constraint(db_repo, async_engine):
    """Inserting an audit with a non-existent goal_id must fail at the FK."""
    from sqlalchemy import text as sa_text
    from sqlalchemy.exc import IntegrityError

    # SQLite needs PRAGMA foreign_keys=ON per connection to enforce FK.
    # Issue it via the engine's connection before running the test action.
    async with async_engine.connect() as conn:
        await conn.execute(sa_text("PRAGMA foreign_keys = ON"))
        await conn.commit()

    svc = DecisionService(db_repo)
    with pytest.raises(IntegrityError):
        await svc.record(
            goal_id="does-not-exist",
            actor=DecisionActor.CODEX,
            rationale="r",
            chosen="c",
        )'''

assert old_fk in src, "old F003 FK block not found"
src = src.replace(old_fk, new_fk)

p.write_text(src, encoding="utf-8")
print("F003 test bugs patched successfully")