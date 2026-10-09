"""mock_tasks.py - 100 deterministic mock tasks for AIOS Kernel simulation harness.

Design:
- 5 task types × 20 tasks each = 100 tasks
- Generation is deterministic via seed=42 (re-runnable)
- Each task carries id, type, success_criteria, budget, deadline, preferred_worker
- Consumed by runner.py and test_simulation_e2e.py
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Dict

TASK_TYPES = ("file_summary", "string_format", "math_calc", "env_probe", "cross_worker")
TASKS_PER_TYPE = 20
TOTAL_TASKS = len(TASK_TYPES) * TASKS_PER_TYPE  # 100
SEED = 42

# Preferred worker hints per type (advisory; T0034 will map to real adapters)
DEFAULT_WORKER_HINTS = {
    "file_summary": "CodexAdapter",
    "string_format": "ClaudeCodeAdapter",
    "math_calc": "HermesAdapter",
    "env_probe": "OpenClawAdapter",
    "cross_worker": "CodexAdapter",
}


@dataclass
class MockTask:
    id: str
    type: str
    title: str
    payload: Dict[str, Any]
    success_criteria: str
    budget: float
    deadline: datetime
    preferred_worker: str
    created_at: datetime
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "payload": self.payload,
            "success_criteria": self.success_criteria,
            "budget": self.budget,
            "deadline": self.deadline.isoformat(),
            "preferred_worker": self.preferred_worker,
            "created_at": self.created_at.isoformat(),
            "priority": self.priority,
        }


def _build_payload(task_type: str, idx: int) -> Dict[str, Any]:
    if task_type == "file_summary":
        return {
            "path": f"D:/ai_mock/file_{idx:03d}.txt",
            "max_lines": 80,
            "language": "zh-Hans" if idx % 2 == 0 else "en",
        }
    if task_type == "string_format":
        return {
            "template": "Task {idx} -> {name} [priority={p}]",
            "vars": {"idx": idx, "name": f"item_{idx}", "p": (idx % 5) + 1},
        }
    if task_type == "math_calc":
        op = ("add", "sub", "mul", "div", "mod")[idx % 5]
        return {"op": op, "a": idx * 7, "b": max(1, idx % 11)}
    if task_type == "env_probe":
        return {
            "probe": ("cpu", "mem", "disk", "net", "proc")[idx % 5],
            "host": f"host-{idx % 4}",
        }
    return {
        "stages": ["stage_a", "stage_b", "stage_c"][: 1 + (idx % 3)],
        "collaborators": ["CodexAdapter", "HermesAdapter", "ClaudeCodeAdapter"][: 1 + (idx % 3)],
    }


def _success_criteria(task_type: str, idx: int) -> str:
    if task_type == "file_summary":
        return f"summary contains 3 key points and length<={80 + idx}"
    if task_type == "string_format":
        return f"formatted string equals 'Task {idx} -> item_{idx} [priority={(idx % 5) + 1}]'"
    if task_type == "math_calc":
        return "result within 1e-9 of expected"
    if task_type == "env_probe":
        return f"probe returns numeric value >=0 within 5s"
    return "all stages completed with verifier PASS"


def _budget(task_type: str, idx: int) -> float:
    base = {
        "file_summary": 1.5,
        "string_format": 0.3,
        "math_calc": 0.2,
        "env_probe": 0.8,
        "cross_worker": 2.2,
    }[task_type]
    return round(base + (idx % 7) * 0.05, 3)


def _priority(idx: int) -> int:
    return ((idx * 13) % 9) + 1  # 1..9


def build_mock_tasks(
    seed: int = SEED,
    base_time: Optional[datetime] = None,
    deadline_window_seconds: int = 3600,
) -> List[MockTask]:
    """Build 100 deterministic mock tasks (5 types × 20).

    Args:
        seed: deterministic RNG seed (default 42).
        base_time: optional base_time anchor (testable); default = 2026-10-08T00:00:00Z.
        deadline_window_seconds: deadline = base_time + offset seconds.

    Returns:
        List of 100 MockTask in deterministic order.
    """
    rng = random.Random(seed)
    if base_time is None:
        base_time = datetime(2026, 10, 8, 0, 0, 0, tzinfo=timezone.utc)

    tasks: List[MockTask] = []
    counter = 0
    for t_type in TASK_TYPES:
        for idx in range(TASKS_PER_TYPE):
            offset = rng.randint(60, deadline_window_seconds)
            created_offset = rng.randint(0, 60)
            tasks.append(
                MockTask(
                    id=f"task-{t_type}-{idx:03d}",
                    type=t_type,
                    title=f"{t_type} #{idx}",
                    payload=_build_payload(t_type, idx),
                    success_criteria=_success_criteria(t_type, idx),
                    budget=_budget(t_type, idx),
                    deadline=base_time + timedelta(seconds=offset),
                    preferred_worker=DEFAULT_WORKER_HINTS[t_type],
                    created_at=base_time + timedelta(seconds=created_offset),
                    priority=_priority(idx),
                )
            )
            counter += 1
    assert counter == TOTAL_TASKS, f"expected {TOTAL_TASKS} tasks, got {counter}"
    return tasks


def build_mock_tasks_by_type(seed: int = SEED) -> Dict[str, List[MockTask]]:
    """Same as build_mock_tasks() but grouped by type."""
    grouped: Dict[str, List[MockTask]] = {t: [] for t in TASK_TYPES}
    for t in build_mock_tasks(seed=seed):
        grouped[t.type].append(t)
    return grouped


if __name__ == "__main__":
    # Smoke test (deterministic)
    t1 = build_mock_tasks(seed=42)
    t2 = build_mock_tasks(seed=42)
    assert len(t1) == 100 == len(t2)
    assert all(a.id == b.id and a.budget == b.budget for a, b in zip(t1, t2))
    by_type = build_mock_tasks_by_type(seed=42)
    assert all(len(v) == 20 for v in by_type.values()), {k: len(v) for k, v in by_type.items()}
    print(f"OK: {len(t1)} tasks, deterministic across runs, 5 types x 20")
    print(f"sample: {t1[0].id} type={t1[0].type} budget={t1[0].budget} priority={t1[0].priority}")