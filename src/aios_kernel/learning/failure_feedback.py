r"""failure_feedback.py - Failure 反哺到 GoalContract (Phase G G001).

闭合学习闭环:
    FailurePatternMerger (F004) -> FailureFeedbackService -> GoalContract.failure_modes

设计原则:
- 只读 + 写 Goal.failure_modes; 不重写 Goal / FailureMode / FailurePatternMerger
- Atomic write: 写失败自动回滚, 不能部分写
- Idempotent: 同一 cluster 重复 apply 不会增加重复 FailureMode
- min_occurrence 阈值: occurrence_count >= N 才反哺 (避免 noise)
- 复用 F004 clusters_to_failure_modes 转换逻辑 (DRY)

Card: D:\AIOS\aios_tasks\aios_vnext\cards\G001_failure_feedback.md
"""
from __future__ import annotations

import logging
from typing import ClassVar, Protocol, runtime_checkable

from aios_kernel.domain.goal import FailureMode, Goal
from aios_kernel.learning.clustering import FailureCluster
from aios_kernel.learning.merger import clusters_to_failure_modes

log = logging.getLogger(__name__)

# 反哺阈值: cluster occurrence >= N 才写回 (避免 noise)
DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK = 3

# 防止单 goal 被无限 fan-out; 100 足够覆盖日常
MAX_MODES_PER_APPLY = 100


@runtime_checkable
class _GoalRepo(Protocol):
    """狭义 contract: 我们只需要 get(Goal, id) + find(Goal, status=...).

    这里用 Protocol 而不是直接 import Repository 是为了
    避免和 InMemoryRepository / SqlAlchemyRepository 耦合;
    任何 duck-typed 仓库都可以被注入.
    """

    async def get(self, model: type, pk: str):
        ...

    async def find(self, model: type, **filters):
        ...


class FailureFeedbackService:
    """Failure cluster -> GoalContract.failure_modes 反哺服务.

    Usage:
        service = FailureFeedbackService(repo, goal_repo)
        updated_goal, added = await service.apply_clusters_to_goal(goal_id, clusters)
        # 或:
        results = await service.apply_clusters_to_active_goals(clusters)
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    def __init__(self, repo, goal_repo):
        # 接受任意 duck-typed repo; InMemoryRepository 和 SqlAlchemyRepository
        # 都满足 (有 add / commit / get / find).
        self.repo = repo
        self.goal_repo = goal_repo

    async def _fetch_goal(self, goal_id: str) -> Goal | None:
        """Fetch a Goal as a Pydantic domain object (cross InMemory / SqlAlchemy).

        SqlAlchemyRepository.get returns an ORM row; we need a Pydantic Goal
        so that validate_assignment re-runs and so that repo.add(goal) can
        map it back via _TO_ORM[Goal]. InMemoryRepository only has get and
        stores Pydantic directly.
        """
        get_domain = getattr(self.goal_repo, "get_domain", None)
        if get_domain is not None:
            return await get_domain(Goal, goal_id)
        return await self.goal_repo.get(Goal, goal_id)

    # ----- 内部 helper ---------------------------------------------------

    @staticmethod
    def _make_failure_mode(cluster: FailureCluster) -> FailureMode:
        """构造一个 FailureMode; 复用 F004 clusters_to_failure_modes 保证一致性."""
        # clusters_to_failure_modes 是 idempotent key (description, detection)
        modes = clusters_to_failure_modes(
            [cluster], min_occurrence=1  # 这里已经过了外层阈值过滤
        )
        if not modes:
            # 极小概率 (cluster.occurrence_count=0); 仍要构造一个
            return FailureMode(
                description=f"[{cluster.root_cause}] {cluster.error_type} (occurs 0x)",
                detection=f"error_type={cluster.error_type}; normalized_hash={cluster.cluster_id[:8]}",
                indicator=cluster.sample_error_messages[0] if cluster.sample_error_messages else None,
            )
        return modes[0]

    @staticmethod
    def _idempotency_keys(goal: Goal) -> set[tuple[str, str]]:
        """返回现有 failure_modes 的 (description, detection) 集合."""
        return {(fm.description, fm.detection) for fm in goal.failure_modes}

    # ----- 公开 API -------------------------------------------------------

    async def apply_clusters_to_goal(
        self,
        goal_id: str,
        clusters: list[FailureCluster],
        min_occurrence: int = DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK,
    ) -> tuple[Goal, list[str]]:
        """把 cluster 转成 FailureMode 写回 Goal (单 goal atomic).

        Returns:
            (updated_goal, added_descriptions)
            updated_goal 是写入后的 Goal (in-memory Pydantic 对象)
            added_descriptions 是本次新增的 FailureMode.description 列表

        Raises:
            ValueError: goal_id 不存在 / min_occurrence < 1
            TypeError: clusters 含非 FailureCluster 元素
        """
        if min_occurrence < 1:
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
            return None, []

        # 构造新的 FailureMode 列表 (idempotent merge)
        existing_keys = self._idempotency_keys(goal)
        new_modes = list(goal.failure_modes)
        added: list[str] = []

        for c in clusters:
            if not isinstance(c, FailureCluster):
                raise TypeError(
                    f"clusters must contain FailureCluster instances, got {type(c).__name__}"
                )
            if c.occurrence_count < min_occurrence:
                continue
            fm = self._make_failure_mode(c)
            key = (fm.description, fm.detection)
            if key in existing_keys:
                continue  # idempotent
            if len(new_modes) - len(goal.failure_modes) >= MAX_MODES_PER_APPLY:
                log.warning(
                    "failure_feedback: hit MAX_MODES_PER_APPLY=%d for goal=%s, truncating",
                    MAX_MODES_PER_APPLY,
                    goal_id,
                )
                break
            new_modes.append(fm)
            existing_keys.add(key)
            added.append(fm.description)

        if not added:
            log.info(
                "failure_feedback: no new modes for goal=%s "
                "(all %d clusters already present or below threshold)",
                goal_id,
                len(clusters),
            )
            return goal, []

        # atomic write: 备份 -> 写 -> commit; 失败回滚
        old_modes = list(goal.failure_modes)
        goal.failure_modes = new_modes
        try:
            await self.repo.add(goal)
            await self.repo.commit()
            log.info(
                "failure_feedback: applied %d new modes to goal=%s",
                len(added),
                goal_id,
            )
            return goal, added
        except Exception as e:
            # rollback: 还原 in-memory 状态, 重抛让外层感知
            goal.failure_modes = old_modes
            log.error(
                "failure_feedback: atomic write failed for goal=%s, rolled back: %s",
                goal_id,
                e,
            )
            raise

    async def apply_clusters_to_active_goals(
        self,
        clusters: list[FailureCluster],
        min_occurrence: int = DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK,
    ) -> dict[str, list[str]]:
        """把所有 active Goal 都加新 FailureMode.

        Returns:
            {goal_id: [added_description, ...]}
            单个 goal 失败不阻塞 batch (其 entry 为空 list + 错误日志)
        """
        active_goals = await self.goal_repo.find(Goal, status="Active")
        results: dict[str, list[str]] = {}
        for goal in active_goals:
            try:
                _, added = await self.apply_clusters_to_goal(goal.id, clusters, min_occurrence)
                results[goal.id] = added
            except Exception as e:
                # 单个 goal 失败不应该阻塞 batch
                log.error(
                    "failure_feedback: goal=%s failed in batch: %s", goal.id, e
                )
                results[goal.id] = []
        return results


__all__ = [
    "FailureFeedbackService",
    "DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK",
    "MAX_MODES_PER_APPLY",
]
