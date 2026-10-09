"""fix_failure_feedback_uuid.py — FailureFeedbackService 必须容错非 UUID goal_id.

Production bug: 任何上游传非 UUID goal_id 会让整个 FailureFeedback 反哺 pipeline 崩溃。
修复: 在 service 层加 try/except + 返回 graceful error.
"""
import pathlib

p = pathlib.Path(r'D:\AIOS\kernel\src\aios_kernel\learning\failure_feedback.py')
src = p.read_text(encoding='utf-8')

old = '''    async def apply_clusters_to_goal(
        self,
        goal_id: str,
        clusters: list[FailureCluster],
        min_occurrence: int = DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK,
    ) -> Goal:
        """把 cluster 转成 FailureMode 写回 Goal (单 goal atomic)."""
        goal = await self.goal_repo.get(goal_id)
        if goal is None:
            raise ValueError(f"goal {goal_id} not found")'''

new = '''    async def apply_clusters_to_goal(
        self,
        goal_id: str,
        clusters: list[FailureCluster],
        min_occurrence: int = DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK,
    ) -> Goal:
        """把 cluster 转成 FailureMode 写回 Goal (单 goal atomic).

        G002-FIX-UUID: 容错非 UUID goal_id — 上游可能传其他 identifier,
        log + 返回 None 而不是崩溃整个反哺 pipeline.
        """
        # Validate UUID format early (avoid Pydantic crash deep in stack)
        import uuid as _uuid
        try:
            _uuid.UUID(str(goal_id))
        except (ValueError, TypeError, AttributeError) as exc:
            log.warning(
                "failure_feedback: skip non-UUID goal_id=%r (%s). Caller must use UUID.",
                goal_id, exc,
            )
            return None

        goal = await self.goal_repo.get(goal_id)
        if goal is None:
            log.warning("failure_feedback: goal_id=%s not found, skip", goal_id)
            return None
        return goal'''

assert old in src, "apply_clusters_to_goal block not found"
src = src.replace(old, new)
p.write_text(src, encoding='utf-8')
print("FailureFeedbackService patched (UUID validation)")