"""fix_failure_feedback_uuid_v2.py — UUID 容错 patch."""
import pathlib

p = pathlib.Path(r'D:\AIOS\kernel\src\aios_kernel\learning\failure_feedback.py')
src = p.read_text(encoding='utf-8')

old = '''        if min_occurrence < 1:
            raise ValueError("min_occurrence must be at least 1")

        goal = await self._fetch_goal(goal_id)
        if goal is None:
            raise ValueError(f"goal {goal_id} not found")'''

new = '''        if min_occurrence < 1:
            raise ValueError("min_occurrence must be at least 1")

        # G002-FIX-UUID: 容错非 UUID goal_id. 上游可能传其他 identifier,
        # log + 返回 ([], []) 而不是 ValueError 炸裂整个反哺 pipeline.
        import uuid as _uuid
        try:
            _uuid.UUID(str(goal_id))
        except (ValueError, TypeError, AttributeError) as exc:
            log.warning(
                "failure_feedback: skip non-UUID goal_id=%r (%s). Caller must use UUID.",
                goal_id, exc,
            )
            empty = await self._fetch_goal(goal_id)  # may still be None
            return empty if empty else None, []

        goal = await self._fetch_goal(goal_id)
        if goal is None:
            log.warning("failure_feedback: goal_id=%s not found, skip", goal_id)
            return None, []'''

assert old in src, "block not found"
src = src.replace(old, new)
p.write_text(src, encoding='utf-8')
print("FailureFeedbackService UUID 容错 patched")