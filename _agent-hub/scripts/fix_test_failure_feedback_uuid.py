"""fix_test_failure_feedback_uuid.py — 适配 UUID 容错的 test."""
import pathlib

p = pathlib.Path(r'D:\AIOS\kernel\tests\unit\test_failure_feedback.py')
src = p.read_text(encoding='utf-8')

old = '''async def test_apply_clusters_goal_not_found_raises():
    repo = InMemoryRepository()
    svc = FailureFeedbackService(repo, repo)
    missing_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="goal " + missing_id + " not found"):
        await svc.apply_clusters_to_goal(missing_id, [_make_cluster()])'''

new = '''async def test_apply_clusters_goal_not_found_returns_empty():
    """G002-FIX-UUID: 容错 non-existent goal_id — 返回 (None, []) 而非 raise.

    防止整个 FailureFeedback pipeline 因单个 missing goal 崩溃.
    """
    repo = InMemoryRepository()
    svc = FailureFeedbackService(repo, repo)
    missing_id = str(uuid.uuid4())
    goal, added = await svc.apply_clusters_to_goal(missing_id, [_make_cluster()])
    assert goal is None
    assert added == []'''

assert old in src, "test block not found"
src = src.replace(old, new)

# Add UUID validation test
old2 = '''async def test_apply_clusters_goal_not_found_returns_empty():'''
new2 = old2  # already exists, leave it

# Append new test for UUID validation
add_test = '''

@pytest.mark.asyncio
async def test_apply_clusters_non_uuid_goal_id_returns_empty():
    """G002-FIX-UUID: 容错非 UUID goal_id — 上游可能传 'P8-T24' 等 identifier.
    返回 (None, []) 而不是 raise ValueError (避免 pipeline 崩溃).
    """
    repo = InMemoryRepository()
    svc = FailureFeedbackService(repo, repo)
    # 'test-goal-001' 不是 UUID
    goal, added = await svc.apply_clusters_to_goal("test-goal-001", [_make_cluster()])
    assert goal is None
    assert added == []
'''

# insert after the empty-return test
insertion_marker = '''async def test_apply_clusters_goal_not_found_returns_empty():
    """G002-FIX-UUID: 容错 non-existent goal_id — 返回 (None, []) 而非 raise.

    防止整个 FailureFeedback pipeline 因单个 missing goal 崩溃.
    """
    repo = InMemoryRepository()
    svc = FailureFeedbackService(repo, repo)
    missing_id = str(uuid.uuid4())
    goal, added = await svc.apply_clusters_to_goal(missing_id, [_make_cluster()])
    assert goal is None
    assert added == []'''

if insertion_marker in src and "test_apply_clusters_non_uuid_goal_id_returns_empty" not in src:
    src = src.replace(insertion_marker, insertion_marker + add_test)

p.write_text(src, encoding='utf-8')
print("test adapted for UUID 容错 + new non-UUID test added")