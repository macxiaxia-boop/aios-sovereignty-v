"""test_false_completion.py - T0036 Part B.

False Completion injection test:
- 5 tasks are executed via T0040 mocks.FakeDoneWorker
- FakeDoneWorker reports success=True but its artifact has evidence_ids=[]
  (deliberate, per T0040 contract)
- A *separate* verifier subprocess (independent process) runs
  tests.sim.mocks.mock_evidence.verify_worker_evidence
- The verifier MUST reject all 5 tasks (verdict = FAIL or BLOCKED)
- Rejection reason must mention "evidence 缺失" / empty / missing

Run with: pytest tests/integration/test_false_completion.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Bootstrap sys.path so we can `import tests.sim.mocks.*`.
_THIS = Path(__file__).resolve()
_KERNEL_ROOT = _THIS.parents[2]
if str(_KERNEL_ROOT) not in sys.path:
    sys.path.insert(0, str(_KERNEL_ROOT))

from tests.sim.mocks.mock_evidence import (  # noqa: E402
    EvidenceRecord,
    MockEvidenceStore,
    verify_worker_evidence,
)
from tests.sim.mocks.mock_workers import (  # noqa: E402
    FakeDoneWorker,
    WorkerFakeDoneException,
    WorkerResult,
)


# ---------------------------------------------------------------------------
# T0036 Part B constants
# ---------------------------------------------------------------------------

FAKE_DONE_COUNT: int = 5

# The verifier's "evidence_ids_empty" reason (T0040 verify_worker_evidence) plus
# the Chinese phrasing the card requires. We accept either — what matters is the
# verifier EXPLICITLY cites the empty-evidence condition.
EVIDENCE_MISSING_TOKENS = (
    "evidence_ids_empty",
    "empty",
    "missing",
    "no_evidence",
    "evidence 缺失",
)


# ---------------------------------------------------------------------------
# Verifier subprocess helper (same shape as Part A)
# ---------------------------------------------------------------------------


def _build_verifier_code(evidence_path: str, kernel_root: str) -> str:
    """Return Python source for an independent verifier subprocess."""
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


def run_verifier_subprocess(evidence_path: str, timeout: int = 30) -> Dict[str, Any]:
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
# FakeDoneWorker execution + evidence dump
# ---------------------------------------------------------------------------


def _run_fake_done_workers(n: int = FAKE_DONE_COUNT) -> List[Dict[str, Any]]:
    """Run n FakeDoneWorker executions and build per-task evidence records.

    Each call to FakeDoneWorker.execute() returns success=True with an
    Artifact whose evidence_ids=[] (per T0040 contract). We faithfully dump
    the *empty* evidence_ids into the JSON so the verifier sees the same
    state the worker reported.
    """
    worker = FakeDoneWorker()
    dump: List[Dict[str, Any]] = []
    for i in range(n):
        task_dict = {
            "id": f"fake-done-task-{i:03d}",
            "type": "math_calc",
            "payload": {"i": i, "claim": "done-but-no-evidence"},
        }
        result: WorkerResult = worker.execute(task_dict)
        # T0040 contract: success=True, fake_done=True, but empty evidence_ids.
        assert result.success is True, f"FakeDoneWorker must report success: {result}"
        assert result.fake_done is True, f"FakeDoneWorker.fake_done flag missing: {result}"
        assert result.artifact is not None
        assert result.artifact.evidence_ids == [], (
            f"FakeDoneWorker.evidence_ids must be empty: {result.artifact}"
        )
        # Deliberately do NOT add fake evidence ids — the verifier must see []
        dump.append(
            {
                "task_id": task_dict["id"],
                "artifact_id": result.artifact.id,
                "evidence_ids": list(result.artifact.evidence_ids),  # = []
                "payload": "fake_done_no_evidence",
                "signed_at": "2026-10-08T00:00:00Z",
                "_fake_done": True,
            }
        )
    return dump


@pytest.fixture(scope="module")
def false_completion_result() -> Dict[str, Any]:
    """Inject 5 FakeDone tasks, then spawn an independent verifier."""
    worker_pid = os.getpid()

    evidence_dump = _run_fake_done_workers(FAKE_DONE_COUNT)
    assert len(evidence_dump) == FAKE_DONE_COUNT
    # Sanity: every record has empty evidence_ids (the injection point)
    for ed in evidence_dump:
        assert ed["evidence_ids"] == [], (
            f"fake_done record {ed['task_id']} somehow has evidence_ids"
        )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        evidence_path = f.name
        json.dump(evidence_dump, f)

    try:
        verifier_output = run_verifier_subprocess(evidence_path, timeout=30)
    finally:
        try:
            os.unlink(evidence_path)
        except OSError:
            pass

    return {
        "worker_pid": worker_pid,
        "verifier_pid": verifier_output["verifier_pid"],
        "verdicts": verifier_output["verdicts"],
        "evidence_dump": evidence_dump,
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_fake_done_5_of_5_rejected(false_completion_result: Dict[str, Any]) -> None:
    """5/5 injected fake-done tasks MUST be rejected by the verifier."""
    verdicts = false_completion_result["verdicts"]
    assert len(verdicts) == FAKE_DONE_COUNT, (
        f"verifier returned {len(verdicts)} verdicts, expected {FAKE_DONE_COUNT}"
    )
    rejections: List[Dict[str, Any]] = []
    false_passes: List[str] = []
    for tid, v in verdicts.items():
        if v.get("verdict") == "PASS":
            false_passes.append(tid)
        elif v.get("verdict") in ("FAIL", "BLOCKED"):
            rejections.append({"task_id": tid, **v})
        else:
            pytest.fail(f"verifier returned unknown verdict for {tid}: {v}")
    assert not false_passes, (
        f"{len(false_passes)} False Completion tasks FALSELY passed: {false_passes}"
    )
    assert len(rejections) == FAKE_DONE_COUNT, (
        f"only {len(rejections)}/{FAKE_DONE_COUNT} rejected"
    )


def test_rejection_verdict_is_fail_or_blocked(
    false_completion_result: Dict[str, Any],
) -> None:
    """Each rejection's verdict must be exactly FAIL or BLOCKED (never PASS)."""
    verdicts = false_completion_result["verdicts"]
    for tid, v in verdicts.items():
        assert v.get("verdict") != "PASS", (
            f"{tid} should be rejected but got PASS — verifier leak!"
        )
        assert v.get("verdict") in ("FAIL", "BLOCKED"), (
            f"{tid} unexpected verdict: {v}"
        )


def test_rejection_reason_mentions_evidence_missing(
    false_completion_result: Dict[str, Any],
) -> None:
    """Every rejection's reason must mention 'evidence 缺失' or equivalent."""
    verdicts = false_completion_result["verdicts"]
    for tid, v in verdicts.items():
        reason = (v.get("reason") or "").lower()
        assert any(
            tok.lower() in reason for tok in EVIDENCE_MISSING_TOKENS
        ), f"{tid} reason does not mention evidence missing: {reason!r}"


def test_fake_done_worker_contract() -> None:
    """Sanity: FakeDoneWorker must report success=True with empty evidence_ids."""
    w = FakeDoneWorker()
    r = w.execute({"id": "task-sanity", "type": "math_calc"})
    assert r.success is True
    assert r.fake_done is True
    assert r.artifact is not None
    assert r.artifact.evidence_ids == []
    # And in-process verifier must reject this contract.
    store = MockEvidenceStore()
    verdict = verify_worker_evidence(store, r.artifact.evidence_ids)
    assert verdict["verdict"] == "FAIL"
    assert verdict["reason"] == "evidence_ids_empty"


def test_verifier_pid_independent_of_worker(
    false_completion_result: Dict[str, Any],
) -> None:
    """Verifier subprocess PID must differ from the worker (test) process PID."""
    worker_pid = false_completion_result["worker_pid"]
    verifier_pid = false_completion_result["verifier_pid"]
    assert isinstance(worker_pid, int) and worker_pid > 0
    assert isinstance(verifier_pid, int) and verifier_pid > 0
    assert worker_pid != verifier_pid, (
        f"verifier_pid ({verifier_pid}) == worker_pid ({worker_pid}); "
        f"verifier MUST be an independent process"
    )


def test_no_false_pass_in_evidence_dump(
    false_completion_result: Dict[str, Any],
) -> None:
    """Cross-check: even an in-process verifier must reject every fake record."""
    verdicts = false_completion_result["verdicts"]
    store = MockEvidenceStore()
    for ed in false_completion_result["evidence_dump"]:
        v = verify_worker_evidence(store, ed["evidence_ids"])
        assert v["verdict"] != "PASS", (
            f"in-process verifier leak on {ed['task_id']}: {v}"
        )
        # and the same task must be rejected by the subprocess verifier
        assert verdicts[ed["task_id"]]["verdict"] != "PASS", (
            f"subprocess verifier leak on {ed['task_id']}"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
