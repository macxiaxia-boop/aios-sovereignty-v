"""fix_test_fk_teardown.py — 修 test_link_to_goal_fk_constraint teardown PendingRollbackError。"""
import pathlib

p = pathlib.Path(r"D:\AIOS\kernel\tests\unit\test_decision_audit.py")
src = p.read_text(encoding="utf-8")

old = '''@pytest.mark.asyncio
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

new = '''@pytest.mark.asyncio
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
    try:
        with pytest.raises(IntegrityError):
            await svc.record(
                goal_id="does-not-exist",
                actor=DecisionActor.CODEX,
                rationale="r",
                chosen="c",
            )
    finally:
        # After IntegrityError, the session is in error state.
        # Rollback so fixture teardown doesn't PendingRollbackError.
        try:
            await db_repo.session.rollback()
        except Exception:
            pass'''

assert old in src, "old block not found"
p.write_text(src.replace(old, new), encoding="utf-8")
print("test_link_to_goal_fk_constraint teardown fixed")