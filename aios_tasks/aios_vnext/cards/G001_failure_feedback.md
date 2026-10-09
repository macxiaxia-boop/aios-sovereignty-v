---
id: G001
title: Failure 反哺到 GoalContract.failure_modes — 学习闭环闭合
owner: CC
priority: P0
track: 7 — VNext Phase G (Learning Closure)
preconditions: [G000, F004, F001]
estimated_minutes: 90
depends_on: [G000, F004, F001]
blocks: [G002, G004]
status: Pending
created: 2026-10-09
codex_supervisor_signoff_required: true
---

## Scope (要做)

把 F004 FailurePatternMerger 归并的 cluster **自动**写回 `GoalContract.failure_modes`，让同类失败下次主动被 GoalGuard 检测。

### 1. 必建/改文件（白名单内）

**`kernel/src/aios_kernel/learning/failure_feedback.py`** — 新建：

```python
"""failure_feedback.py — Failure 反哺到 GoalContract (Phase G G001).

关键: 必须 atomic — 写失败回滚, 不能部分写。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from aios_kernel.domain.goal import Goal, FailureMode
from aios_kernel.learning.clustering import FailureCluster, FailurePatternMerger

log = logging.getLogger(__name__)

# 反哺阈值: cluster occurrence ≥ N min_occurrence 才写回 (避免 noise)
DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK = 3


class FailureFeedbackService:
    """Failure cluster → GoalContract.failure_modes 反哺服务"""
    
    SCHEMA_VERSION: ClassVar[int] = 1
    
    def __init__(self, repo, goal_repo):
        self.repo = repo
        self.goal_repo = goal_repo
    
    async def apply_clusters_to_goal(
        self,
        goal_id: str,
        clusters: list[FailureCluster],
        min_occurrence: int = DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK,
    ) -> Goal:
        """把 cluster 转成 FailureMode 写回 Goal (单 goal atomic)."""
        goal = await self.goal_repo.get(goal_id)
        if goal is None:
            raise ValueError(f"goal {goal_id} not found")
        
        # 构造新的 FailureMode 列表 (idempotent merge)
        existing_keys = {(fm.description, fm.detection) for fm in goal.failure_modes}
        new_modes = list(goal.failure_modes)
        added = []
        
        for c in clusters:
            if c.occurrence_count < min_occurrence:
                continue
            desc = f"[{c.root_cause}] {c.error_type} (occurs {c.occurrence_count}x)"
            detection = f"error_type={c.error_type}; normalized_hash={c.cluster_id[:8]}"
            indicator = c.sample_error_messages[0] if c.sample_error_messages else None
            key = (desc, detection)
            if key in existing_keys:
                continue  # idempotent
            new_modes.append(FailureMode(description=desc, detection=detection, indicator=indicator))
            existing_keys.add(key)
            added.append(desc)
        
        if not added:
            log.info("failure_feedback: no new modes for goal=%s (all %d clusters already present)", goal_id, len(clusters))
            return goal
        
        # atomic write with repo
        old_modes = list(goal.failure_modes)
        goal.failure_modes = new_modes
        try:
            await self.repo.add(goal)
            await self.repo.commit()
            log.info("failure_feedback: applied %d new modes to goal=%s", len(added), goal_id)
            return goal
        except Exception as e:
            # rollback
            goal.failure_modes = old_modes
            log.error("failure_feedback: atomic write failed, rolled back: %s", e)
            raise
    
    async def apply_clusters_to_active_goals(
        self,
        clusters: list[FailureCluster],
    ) -> dict[str, int]:
        """把所有 active Goal 都加新 FailureMode (用于 batch 模式).
        
        Returns: {goal_id: added_count}
        """
        active_goals = await self.goal_repo.find_active()
        results = {}
        for goal in active_goals:
            before = len(goal.failure_modes)
            await self.apply_clusters_to_goal(goal.id, clusters)
            after = len(await self.goal_repo.get(goal.id))
            results[goal.id] = after - before
        return results


__all__ = ["FailureFeedbackService", "DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK"]
```

**`kernel/src/aios_kernel/learning/__init__.py`** — 导出 FailureFeedbackService

**`kernel/tests/unit/test_failure_feedback.py`** — 20+ case

### 2. Scheduled Task 注册脚本

**`D:\AIOS\aios_tasks\aios_vnext\scripts\run_failure_feedback.cmd`** — 每 15 分钟跑一次：

```cmd
@echo off
REM 每 15 分钟跑一次 failure feedback
cd /d D:\AIOS\kernel
D:\AIOS\kernel\.venv\Scripts\python.exe -m aios_kernel.learning.failure_feedback_runner --min-occurrence 3 --interval 900
```

**`kernel/src/aios_kernel/learning/failure_feedback_runner.py`** — main entry:

```python
"""failure_feedback_runner.py — 每 N 分钟跑一次 failure feedback."""
import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from aios_kernel.learning.clustering import FailurePatternMerger
from aios_kernel.learning.failure_feedback import FailureFeedbackService
from aios_kernel.domain.services.repository import make_engine, session_scope
from aios_kernel.persistence.repository import SqlAlchemyRepository
from aios_kernel.persistence.models import GoalORM

log = logging.getLogger("failure_feedback_runner")


async def main(min_occurrence: int, interval_sec: int):
    engine = make_engine()
    factory = ... 
    
    # 1. 读今天的 failure events (from v2 logs or test runs)
    # ... collect failure traces ...
    
    # 2. cluster
    merger = FailurePatternMerger()
    clusters = merger.merge(traces)
    
    # 3. apply to active goals
    async with session_scope(factory) as session:
        repo = SqlAlchemyRepository(session)
        feedback = FailureFeedbackService(repo, repo)
        results = await feedback.apply_clusters_to_active_goals(clusters)
    
    log.info("failure_feedback: applied %s", results)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--min-occurrence", type=int, default=3)
    p.add_argument("--interval", type=int, default=900)
    args = p.parse_args()
    asyncio.run(main(args.min_occurrence, args.interval))
```

### 3. Atomic 保证
- 使用 SQLAlchemy transaction
- 写失败自动 rollback (FailureFeedbackService.apply_clusters_to_goal 已有 try/except)

### 4. 单元测试 (20+ case)

```python
def test_apply_clusters_adds_new_modes()
def test_apply_clusters_idempotent_no_duplicates()
def test_apply_clusters_below_min_occurrence_skipped()
def test_apply_clusters_goal_not_found_raises()
def test_apply_clusters_atomic_rollback_on_error()
def test_apply_clusters_to_active_goals_returns_added_count()
def test_apply_clusters_preserves_existing_modes()
def test_apply_clusters_with_empty_clusters_no_op()
def test_apply_clusters_recognizes_existing_by_description_detection_key()
def test_apply_clusters_idempotent_after_repeated_calls()
def test_apply_clusters_handles_goal_with_empty_failure_modes()
def test_apply_clusters_with_100_clusters_only_top_N_added()
def test_run_failure_feedback_runner_logs_results()
def test_scheduled_task_registration_creates_entry()
def test_atomic_write_rollback_preserves_state()
def test_no_minimum_occurrence_disables_threshold()
def test_failure_modes_count_increases_monotonically()
def test_apply_clusters_includes_severity_in_description()
def test_apply_clusters_includes_normalized_hash_in_detection()
def test_apply_clusters_includes_indicator_from_sample_messages()
```

## Out-of-scope (不要做)

- ❌ 不重写 FailurePatternMerger (F004 已有)
- ❌ 不重写 Goal 模型 (F001 已有 12 字段)
- ❌ 不实现 cross-agent knowledge (G003 才做)
- ❌ 不实现 inbound 循环 (G002 才做)
- ❌ 不改 GoalGuard (F005 已有)
- ❌ 不改 v2 consumer / v2_consumer.py
- ❌ 不创建 `_v6_*.py` / `_r*.py` / `protocol_*.md` 等 forbidden pattern

## Inputs (必须先读)

1. `D:\AIOS\kernel\src\aios_kernel\learning\clustering.py` — F004 已建
2. `D:\AIOS\kernel\src\aios_kernel\domain\goal.py` — F001 已建 (FailureMode schema)
3. `D:\AIOS\aios_tasks\aios_vnext\cards\F004_failure_pattern_merger.md` — FailurePatternMerger 接口
4. `D:\AIOS\aios_tasks\aios_vnext\cards\G000_phase_g_acceptance_spec.md` — Phase G spec
5. `D:\AIOS\aios_tasks\aios_vnext\cards\F001_goal_contract_12_fields.md` — GoalContract schema

## Outputs (必须产出)

1. `D:\AIOS\aios_tasks\aios_vnext\evidence\G001__<ts>.md` — 必含 preflight 附件
2. `D:\AIOS\kernel\src\aios_kernel\learning\failure_feedback.py` — FailureFeedbackService
3. `D:\AIOS\kernel\src\aios_kernel\learning\failure_feedback_runner.py` — CLI runner
4. `D:\AIOS\kernel\src\aios_kernel\learning\__init__.py` — 导出
5. `D:\AIOS\kernel\tests\unit\test_failure_feedback.py` — 20+ case
6. `D:\AIOS\aios_tasks\aios_vnext\scripts\run_failure_feedback.cmd` — Scheduled Task entry
8. 至少 1 次 evidence 文档说明"已运行 runner + 应用到 active goals"

## Evidence Requirements

- [ ] FailureFeedbackService.apply_clusters_to_goal 可 import + 调用
- [ ] 20+ unit case 全 PASS
- [ ] Atomic rollback 验证（写失败状态保留）
- [ ] Idempotent 验证（重复调用不加重复）
- [ ] min_occurrence 阈值过滤验证
- [ ] `apply_clusters_to_active_goals` 返回 added_count dict
- [ ] 至少跑一次 runner，输出 results 写 evidence
- [ ] preflight = 0 issues
- [ ] 现有 Phase A-F + 5 cards Verified baseline 不退化

## Exit Criteria

1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex
3. **不自封 Verified**

## Rollback

1. `git reset --hard HEAD~1`（如有 commit）
2. 删除 `failure_feedback.py` / `failure_feedback_runner.py`
3. 删除 `test_failure_feedback.py`
4. 删除 `run_failure_feedback.cmd`

## Time Budget

90 分钟

## Codex Acceptance Gate

Codex 独立验证：
1. `pytest tests/unit/test_failure_feedback.py -v` 20+ case PASS
2. `python -m aios_kernel.learning.failure_feedback_runner --min-occurrence 3` 实际跑一次输出 results
3. `pytest tests/unit -v` 全套仍 PASS
4. preflight v4 = 0 issues
5. 抽样 5 个新建测试用例各跑一次

通过 → status=Verified