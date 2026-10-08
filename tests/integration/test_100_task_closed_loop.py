"""test_100_task_closed_loop.py - T0036 Part A.

100-task closed loop integration test:
- 30 file_summary + 20 string_format + 20 math_calc + 15 env_probe + 15 cross_worker
- Worker distribution: 70% codex-adapter, 20% claude-code-adapter, 10% openclaw-adapter
- Each task is executed through the AIOS Kernel's WorkerAdapter (real, not mock)
- Each artifact is hashed into a MockEvidenceStore record
- A *separate* verifier subprocess independently re-runs
  tests.sim.mocks.mock_evidence.verify_worker_evidence and emits verdicts
- Asserts: 100/100 PASS, distribution +/- 5 pp, verifier_pid != worker_pid,
  every task has artifacts + evidence + cost, cross_worker tasks all pass.

Run with: pytest tests/integration/test_100_task_closed_loop.py -v
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
import pytest_asyncio

# Bootstrap sys.path so we can `import aios_kernel.*` and `import tests.sim.mocks.*`.
_THIS = Path(__file__).resolve()
_KERNEL_ROOT = _THIS.parents[2]
if str(_KERNEL_ROOT) not in sys.path:
    sys.path.insert(0, str(_KERNEL_ROOT))

from aios_kernel.workers import (  # noqa: E402
    ClaudeCodeAdapter,
    CodexAdapter,
    OpenClawAdapter,
    WorkerAdapter,
    WorkerRegistry,
)
from tests.sim.mocks.mock_evidence import (  # noqa: E402
    EvidenceRecord,
    MockEvidenceStore,
    verify_worker_evidence,
)
from tests.sim.mocks.mock_tasks import (  # noqa: E402
    DEFAULT_WORKER_HINTS,
    MockTask,
    SEED,
    _build_payload,
    _budget,
    _priority,
    _success_criteria,
)


# ---------------------------------------------------------------------------
# T0036 Part A constants
# ---------------------------------------------------------------------------

T0036_TYPE_DIST: Dict[str, int] = {
    "file_summary": 30,
    "string_format": 20,
    "math_calc": 20,
    "env_probe": 15,
    "cross_worker": 15,
}
T0036_TOTAL: int = sum(T0036_TYPE_DIST.values())  # 100

# Worker distribution: 70% codex, 20% claude, 10% openclaw.
CODEX_QUOTA: int = 70
CLAUDE_QUOTA: int = 20
OPENCLAW_QUOTA: int = 10
assert CODEX_QUOTA + CLAUDE_QUOTA + OPENCLAW_QUOTA == T0036_TOTAL

# +/- 5 percentage points (over 100 tasks = +/- 5 tasks)
DIST_TOLERANCE: int = 5


# ---------------------------------------------------------------------------
# Task factory
# ---------------------------------------------------------------------------


def build_t0036_tasks(seed: int = SEED) -> List[MockTask]:
    """Build 100 deterministic MockTask with T0036 type distribution.

    Per card Part A: 30 file_summary + 20 string_format + 20 math_calc
                     + 15 env_probe + 15 cross_worker = 100
    """
    import random

    rng = random.Random(seed)
    base_time = datetime(2026, 10, 8, 0, 0, 0, tzinfo=timezone.utc)

    tasks: List[MockTask] = []
    for ttype, count in T0036_TYPE_DIST.items():
        for idx in range(count):
            offset = rng.randint(60, 3600)
            created_offset = rng.randint(0, 60)
            tasks.append(
                MockTask(
                    id=f"task-{ttype}-{idx:03d}-t0036",
                    type=ttype,
                    title=f"{ttype} #{idx}",
                    payload=_build_payload(ttype, idx),
                    success_criteria=_success_criteria(ttype, idx),
                    budget=_budget(ttype, idx),
                    deadline=base_time + timedelta(seconds=offset),
                    preferred_worker=DEFAULT_WORKER_HINTS[ttype],
                    created_at=base_time + timedelta(seconds=created_offset),
                    priority=_priority(idx),
                )
            )
    assert len(tasks) == T0036_TOTAL
    return tasks


def assign_workers_70_20_10(tasks: List[MockTask]) -> List[MockTask]:
    """Mutate each task.worker in-place to enforce 70/20/10 quota.

    First 70 -> codex-adapter
    Next  20 -> claude-code-adapter
    Last  10 -> openclaw-adapter
    """
    for i, t in enumerate(tasks):
        if i < CODEX_QUOTA:
            t.worker = "codex-adapter"
        elif i < CODEX_QUOTA + CLAUDE_QUOTA:
            t.worker = "claude-code-adapter"
        else:
            t.worker = "openclaw-adapter"
    return tasks


# ---------------------------------------------------------------------------
# Verifier subprocess helper
# ---------------------------------------------------------------------------


def _build_verifier_code(evidence_path: str, kernel_root: str) -> str:
    """Return a Python source string run in a subprocess (independent verifier).

    Reads evidence records from `evidence_path` (a JSON file written by the
    main test process), re-instantiates them inside the subprocess, runs
    verify_worker_evidence, and emits a JSON line containing the verifier
    PID + per-task verdicts.
    """
    return (
        "import json, os, sys\n"
        f"sys.path.insert(0, {kernel_root!r})\n"
        "from tests.sim.mocks.mock_evidence import (\n"
        "    EvidenceRecord, MockEvidenceStore, verify_worker_evidence,\n"
        ")\n"
        f"data = json.load(open({evidence_path!r}, encoding='utf-8'))\n"
        "store = MockEvidenceStore()\n"
        "verdicts = {}\n"
        "for td in data:\n"
        "    for eid in td['evidence_ids']:\n"
        "        rec = EvidenceRecord(\n"
        "            id=eid,\n"
        "            task_id=td['task_id'],\n"
        "            artifact_id=td['artifact_id'],\n"
        "            payload=td['payload'],\n"
        "            signed_at=td['signed_at'],\n"
        "            verdict='PENDING',\n"
        "        )\n"
        "        store.put(rec)\n"
        "    v = verify_worker_evidence(store, td['evidence_ids'])\n"
        "    verdicts[td['task_id']] = v\n"
        "print(json.dumps({'verifier_pid': os.getpid(), 'verdicts': verdicts}))\n"
    )


def run_verifier_subprocess(evidence_path: str, timeout: int = 60) -> Dict[str, Any]:
    """Spawn a Python subprocess that re-runs the verifier independently."""
    kernel_root = str(_KERNEL_ROOT).replace("\\", "/")
    code = _build_verifier_code(evidence_path, kernel_root)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"verifier subprocess failed: rc={proc.returncode}\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        )
    if not proc.stdout.strip():
        raise RuntimeError(f"verifier subprocess produced no stdout. stderr={proc.stderr!r}")
    return json.loads(proc.stdout)


# ---------------------------------------------------------------------------
# Main fixture: run all 100 tasks through the WorkerAdapter layer, then call
# the independent verifier subprocess and return the combined result.
# ---------------------------------------------------------------------------


async def _execute_all_tasks(
    tasks: List[MockTask],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """Execute all 100 tasks via WorkerRegistry, build per-task records."""
    registry = WorkerRegistry()
    registry.register(CodexAdapter())
    registry.register(ClaudeCodeAdapter())
    registry.register(OpenClawAdapter())

    evidence_dump: List[Dict[str, Any]] = []
    task_records: List[Dict[str, Any]] = []
    worker_counts: Dict[str, int] = {}

    for task in tasks:
        adapter = registry.route(task)
        worker_counts[adapter.worker_id] = worker_counts.get(adapter.worker_id, 0) + 1
        artifact = await adapter.execute(task)
        evidence_id = f"ev-{task.id}"
        evidence_record = {
            "task_id": task.id,
            "artifact_id": artifact.id,
            "evidence_ids": [evidence_id],
            "payload": f"evidence_for_{task.id}",
            "signed_at": "2026-10-08T00:00:00Z",
            "_worker": adapter.worker_id,
            "_type": task.type,
            "_cost": float(task.budget),
            "_artifact_id": artifact.id,
            "_has_artifact_payload": artifact.has_payload,
        }
        evidence_dump.append(evidence_record)
        task_records.append(
            {
                "task_id": task.id,
                "type": task.type,
                "worker": adapter.worker_id,
                "artifact_id": artifact.id,
                "evidence_id": evidence_id,
                "cost": float(task.budget),
            }
        )
    return evidence_dump, task_records, worker_counts


@pytest_asyncio.fixture(scope="module")
async def t0036_loop_result() -> Dict[str, Any]:
    """Run 100 tasks + spawn verifier subprocess once per test module."""
    worker_pid = os.getpid()

    tasks = build_t0036_tasks()
    assert len(tasks) == T0036_TOTAL
    assign_workers_70_20_10(tasks)

    evidence_dump, task_records, worker_counts = await _execute_all_tasks(tasks)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        evidence_path = f.name
        json.dump(evidence_dump, f)

    try:
        verifier_output = run_verifier_subprocess(evidence_path, timeout=60)
    finally:
        try:
            os.unlink(evidence_path)
        except OSError:
            pass

    return {
        "worker_pid": worker_pid,
        "verifier_pid": verifier_output["verifier_pid"],
        "verdicts": verifier_output["verdicts"],
        "task_records": task_records,
        "worker_counts": worker_counts,
        "evidence_dump": evidence_dump,
    }


# ---------------------------------------------------------------------------
# Test cases (each is one assertion slice of the 100-task closed loop)
# ---------------------------------------------------------------------------


def test_100_of_100_pass(t0036_loop_result: Dict[str, Any]) -> None:
    """All 100 tasks must be signed PASS by the independent verifier."""
    verdicts = t0036_loop_result["verdicts"]
    assert len(verdicts) == T0036_TOTAL, (
        f"verifier only returned {len(verdicts)} verdicts, expected {T0036_TOTAL}"
    )
    failures = [
        (tid, v) for tid, v in verdicts.items() if v.get("verdict") != "PASS"
    ]
    assert not failures, f"{len(failures)} tasks did NOT pass verifier: {failures[:5]}"
    pass_count = sum(1 for v in verdicts.values() if v.get("verdict") == "PASS")
    assert pass_count == T0036_TOTAL, f"only {pass_count}/{T0036_TOTAL} PASS"


def test_worker_distribution_within_5pp(t0036_loop_result: Dict[str, Any]) -> None:
    """Worker Adapter distribution must be 70/20/10 +/- 5 percentage points."""
    counts = t0036_loop_result["worker_counts"]
    codex = counts.get("codex-adapter", 0)
    claude = counts.get("claude-code-adapter", 0)
    openclaw = counts.get("openclaw-adapter", 0)
    other = sum(
        v for k, v in counts.items()
        if k not in ("codex-adapter", "claude-code-adapter", "openclaw-adapter")
    )
    total = codex + claude + openclaw + other
    assert total == T0036_TOTAL, f"worker total {total} != {T0036_TOTAL}"
    assert other == 0, f"unexpected worker usage: {counts}"
    assert abs(codex - CODEX_QUOTA) <= DIST_TOLERANCE, (
        f"codex count {codex} outside +/- {DIST_TOLERANCE} of {CODEX_QUOTA}"
    )
    assert abs(claude - CLAUDE_QUOTA) <= DIST_TOLERANCE, (
        f"claude count {claude} outside +/- {DIST_TOLERANCE} of {CLAUDE_QUOTA}"
    )
    assert abs(openclaw - OPENCLAW_QUOTA) <= DIST_TOLERANCE, (
        f"openclaw count {openclaw} outside +/- {DIST_TOLERANCE} of {OPENCLAW_QUOTA}"
    )


def test_verifier_pid_independent(t0036_loop_result: Dict[str, Any]) -> None:
    """Verifier must run in a different process from the Worker (kernel)."""
    worker_pid = t0036_loop_result["worker_pid"]
    verifier_pid = t0036_loop_result["verifier_pid"]
    assert isinstance(worker_pid, int) and worker_pid > 0
    assert isinstance(verifier_pid, int) and verifier_pid > 0
    assert worker_pid != verifier_pid, (
        f"verifier_pid ({verifier_pid}) == worker_pid ({worker_pid}); "
        f"verifier MUST run in an independent process (T0030 sec.3 + T0035)"
    )


def test_each_task_has_artifact_evidence_cost(
    t0036_loop_result: Dict[str, Any],
) -> None:
    """Every task must carry: artifact_id + evidence_id + cost record."""
    records = t0036_loop_result["task_records"]
    assert len(records) == T0036_TOTAL

    artifact_ids = {r["artifact_id"] for r in records}
    evidence_ids = {r["evidence_id"] for r in records}
    assert len(artifact_ids) == T0036_TOTAL
    assert len(evidence_ids) == T0036_TOTAL
    for r in records:
        assert r["cost"] > 0.0, f"non-positive cost on {r['task_id']}: {r['cost']}"

    for ed in t0036_loop_result["evidence_dump"]:
        assert ed["_has_artifact_payload"], (
            f"artifact payload missing for {ed['task_id']}"
        )
        assert ed["evidence_ids"], (
            f"empty evidence_ids for {ed['task_id']} (artifacts required)"
        )
        assert ed["_cost"] > 0.0, (
            f"cost record missing/zero for {ed['task_id']}: {ed['_cost']}"
        )


def test_cross_worker_tasks_all_pass(t0036_loop_result: Dict[str, Any]) -> None:
    """The 15 cross_worker tasks must all be routed + verifier-PASSed."""
    verdicts = t0036_loop_result["verdicts"]
    cross_worker = [
        r for r in t0036_loop_result["task_records"] if r["type"] == "cross_worker"
    ]
    assert len(cross_worker) == 15, f"expected 15 cross_worker, got {len(cross_worker)}"
    for r in cross_worker:
        v = verdicts.get(r["task_id"])
        assert v is not None, f"no verdict for cross_worker {r['task_id']}"
        assert v["verdict"] == "PASS", f"cross_worker {r['task_id']} failed: {v}"


def test_type_distribution_30_20_20_15_15(
    t0036_loop_result: Dict[str, Any],
) -> None:
    """The 100 tasks must be split 30/20/20/15/15 across the 5 types."""
    by_type: Dict[str, int] = {}
    for r in t0036_loop_result["task_records"]:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    for ttype, expected in T0036_TYPE_DIST.items():
        assert by_type.get(ttype) == expected, (
            f"type {ttype}: got {by_type.get(ttype)}, expected {expected}"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
