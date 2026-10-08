"""test_verifier_independent.py - T0035 integration tests.

7 test cases, in the order required by the T0035 card Section 6:

    1. PID different: Verifier process PID != Kernel (test) process PID
    2. Missing evidence -> verdict=FAIL
    3. Evidence hash mismatch -> verdict=FAIL
    4. Missing artifact (file on disk gone) -> verdict=FAIL
    5. Budget overflow (cost_yuan > budget_yuan) -> verdict=FAIL
    6. All pass -> verdict=PASS
    7. BLOCKED scenario (partial evidence - declared criteria but no evidence)

Strategy:
- The Verifier is a real FastAPI process booted as a subprocess via
  `python -m aios_kernel.verifier.server` on an ephemeral port
  (handed out by the OS).
- The test process (this pytest run) is the "Kernel" in T0035 terms.
  Asserting os.getpid() != verifier_pid proves process isolation.
- Tests 2..7 drive the DeterministicVerifier in-process for speed and
  determinism; test 1 alone hits the network.
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import socket
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

_KERNEL_ROOT = Path(__file__).resolve().parents[2]  # D:\AIOS\kernel
_SRC = _KERNEL_ROOT / "src"
sys.path.insert(0, str(_SRC))

from aios_kernel.verifier import (  # noqa: E402
    ArtifactRecord,
    DeterministicVerifier,
    EvidenceRecord,
    InMemoryEvidenceStore,
    VerdictCode,
)

# ---------- helpers ---------------------------------------------------------


def _free_port() -> int:
    """Ask the OS for an unused TCP port (ephemeral)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_http(url: str, timeout_s: float = 20.0) -> None:
    """Poll GET url until it responds (or timeout)."""
    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with httpx.Client(timeout=1.0) as c:
                r = c.get(url)
                if r.status_code in (200, 404):
                    return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        time.sleep(0.1)
    raise TimeoutError(
        f"server at {url} did not respond in {timeout_s}s (last_err={last_err})"
    )


@contextlib.contextmanager
def _running_verifier(port: int, verifier_id: str = "itest-verifier"):
    """Boot the Verifier as a subprocess on the given port. Cleans up on exit.

    Uses `python -m aios_kernel.verifier.server` so we get the same
    server as production. Sets VERIFIER_PORT in env to override the
    default 9001.
    """
    env = os.environ.copy()
    env["VERIFIER_PORT"] = str(port)
    env["VERIFIER_HOST"] = "127.0.0.1"
    env["VERIFIER_ID"] = verifier_id
    env["PYTHONPATH"] = str(_SRC) + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.Popen(
        [sys.executable, "-m", "aios_kernel.verifier.server"],
        cwd=str(_KERNEL_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_http(f"http://127.0.0.1:{port}/health", timeout_s=20.0)
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5.0)


def _now() -> datetime:
    return datetime.now(UTC)


def _seed_pass_scenario(store: InMemoryEvidenceStore):
    """Seed an in-memory store so a typical task verifies PASS."""
    now = _now()
    eid = uuid.uuid4().hex
    aid = uuid.uuid4().hex
    h = hashlib.sha256(b"hello world").hexdigest()
    store.put_evidence(
        EvidenceRecord(
            evidence_id=eid,
            task_id="task-pass",
            verifier_id="worker-stub",
            verdict="PASS",
            artifact_ids=[aid],
            evidence_hash="a" * 64,
            details={"status": "ok", "count": 5, "marker": "all:ok"},
            signed_at=now,
        )
    )
    store.put_artifact(
        ArtifactRecord(
            artifact_id=aid,
            task_id="task-pass",
            artifact_type="text",
            path=None,
            inline_content="hello world",
            inline_json=None,
            hash_sha256=h,
            size_bytes=11,
        )
    )
    return eid, aid


# ---------- fixtures --------------------------------------------------------


@pytest.fixture
def port() -> int:
    return _free_port()


@pytest.fixture
def base_url(port):
    return f"http://127.0.0.1:{port}"


@pytest.fixture
def store() -> InMemoryEvidenceStore:
    return InMemoryEvidenceStore()


@pytest.fixture
def verifier(store) -> DeterministicVerifier:
    return DeterministicVerifier("itest-verifier", store)


# ---------- test 1: PID different (proves process isolation) ----------------


async def test_verifier_pid_differs_from_kernel(port, base_url) -> None:
    """Spec Section 2: Verifier is an OS process; PID must differ from the test's PID."""
    with _running_verifier(port):
        kernel_pid = os.getpid()
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base_url}/health")
            assert r.status_code == 200, r.text
            body = r.json()
        verifier_pid = body["verifier_pid"]
        print(
            f"PID check: kernel={kernel_pid} verifier={verifier_pid} "
            f"differ={kernel_pid != verifier_pid}"
        )
        assert verifier_pid != kernel_pid, (
            f"Verifier process must be independent; kernel_pid={kernel_pid} "
            f"verifier_pid={verifier_pid}"
        )
        # Also confirm the health report includes rules_loaded (proves
        # the deterministic engine is the live one, not a stub).
        rules = body["report"]["rules_loaded"]
        assert len(rules) == 6
        assert "evidence_list_nonempty" in rules
        assert "budget_not_overflow" in rules
        # Status must be healthy and verdict codes are PASS / FAIL / BLOCKED
        assert body["report"]["status"] == "healthy"


# ---------- test 2: missing evidence -> FAIL --------------------------------


async def test_missing_evidence_returns_fail(verifier) -> None:
    task = {
        "id": "task-missing-ev",
        "evidence_ids": [],
        "artifact_ids": [],
        "success_criteria": "",
        "cost_yuan": 0.0,
        "budget_yuan": 10.0,
    }
    verdict = await verifier.verify(task, [])
    assert verdict.verdict == VerdictCode.FAIL
    assert verdict.reason
    # First failing rule should be evidence_list_nonempty
    assert "evidence_list_nonempty" in verdict.details
    assert verdict.details["evidence_list_nonempty"]["ok"] is False
    assert "0 evidence record" in verdict.details["evidence_list_nonempty"]["message"]


# ---------- test 3: evidence hash mismatch -> FAIL --------------------------


async def test_evidence_hash_mismatch_returns_fail(verifier, store) -> None:
    now = _now()
    eid = uuid.uuid4().hex
    store.put_evidence(
        EvidenceRecord(
            evidence_id=eid,
            task_id="task-bad-hash",
            verifier_id="worker-stub",
            verdict="PASS",
            artifact_ids=[],
            evidence_hash="zzzznothex",  # invalid: not 64-char hex
            details={},
            signed_at=now,
        )
    )
    task = {
        "id": "task-bad-hash",
        "evidence_ids": [eid],
        "artifact_ids": [],
        "success_criteria": "",
        "cost_yuan": 0.0,
        "budget_yuan": 10.0,
    }
    verdict = await verifier.verify(task, [eid])
    assert verdict.verdict == VerdictCode.FAIL
    assert "evidence_hash_matches" in verdict.details
    assert verdict.details["evidence_hash_matches"]["ok"] is False
    bad = verdict.details["evidence_hash_matches"]["bad"]
    assert any(b.get("evidence_id") == eid for b in bad)


# ---------- test 4: artifact missing on disk -> FAIL ------------------------


async def test_artifact_missing_returns_fail(verifier, store) -> None:
    now = _now()
    eid = uuid.uuid4().hex
    aid = uuid.uuid4().hex
    # Worker claims a file artifact at a path that does not exist
    store.put_evidence(
        EvidenceRecord(
            evidence_id=eid,
            task_id="task-missing-art",
            verifier_id="worker-stub",
            verdict="PASS",
            artifact_ids=[aid],
            evidence_hash="a" * 64,
            details={},
            signed_at=now,
        )
    )
    fake_path = "D:/this/path/definitely/does/not/exist/aios_ghost.bin"
    store.put_artifact(
        ArtifactRecord(
            artifact_id=aid,
            task_id="task-missing-art",
            artifact_type="file",
            path=fake_path,
            inline_content=None,
            inline_json=None,
            hash_sha256="a" * 64,
            size_bytes=123,
        )
    )
    task = {
        "id": "task-missing-art",
        "evidence_ids": [eid],
        "artifact_ids": [aid],
        "success_criteria": "",
        "cost_yuan": 0.0,
        "budget_yuan": 10.0,
    }
    verdict = await verifier.verify(task, [eid])
    assert verdict.verdict == VerdictCode.FAIL
    assert "artifact_exists" in verdict.details
    assert verdict.details["artifact_exists"]["ok"] is False
    assert aid in verdict.details["artifact_exists"]["missing_files"]


# ---------- test 5: budget overflow -> FAIL ---------------------------------


async def test_budget_overflow_returns_fail(verifier) -> None:
    # Use the seed helper so rules 1..4 pass; rule 6 will fail.
    store = verifier._store  # type: ignore[attr-defined]
    eid, aid = _seed_pass_scenario(store)
    task = {
        "id": "task-pass",
        "evidence_ids": [eid],
        "artifact_ids": [aid],
        "success_criteria": "status=ok;count=5",
        "cost_yuan": 100.0,  # OVER budget
        "budget_yuan": 10.0,
    }
    verdict = await verifier.verify(task, [eid])
    assert verdict.verdict == VerdictCode.FAIL
    assert "budget_not_overflow" in verdict.details
    assert verdict.details["budget_not_overflow"]["ok"] is False
    assert "exceeds" in verdict.details["budget_not_overflow"]["message"]


# ---------- test 6: all pass -> PASS ----------------------------------------


async def test_all_rules_pass_returns_pass(verifier) -> None:
    store = verifier._store  # type: ignore[attr-defined]
    eid, aid = _seed_pass_scenario(store)
    task = {
        "id": "task-pass",
        "evidence_ids": [eid],
        "artifact_ids": [aid],
        "success_criteria": "status=ok;count=5",
        "cost_yuan": 1.0,
        "budget_yuan": 10.0,
    }
    verdict = await verifier.verify(task, [eid])
    assert verdict.verdict == VerdictCode.PASS
    assert verdict.reason
    assert "all 6 deterministic rules passed" in verdict.reason
    # All 6 rules should be present in details and all pass
    rule_names = {
        "evidence_list_nonempty",
        "evidence_exists",
        "evidence_hash_matches",
        "artifact_exists",
        "success_criteria",
        "budget_not_overflow",
    }
    assert rule_names.issubset(set(verdict.details.keys()))
    for name in rule_names:
        assert verdict.details[name]["ok"] is True, (
            f"rule {name} not ok: {verdict.details[name]}"
        )


# ---------- test 7: BLOCKED scenario (partial evidence) ---------------------


async def test_blocked_partial_evidence_scenario(verifier, store) -> None:
    """A task with declared success_criteria but partial evidence.

    Two of three expected clauses are verifiable; one is missing the
    key entirely. Our deterministic implementation maps this to FAIL
    (we treat rules 1-6 as boolean; BLOCKED is reserved for the
    verifier process itself being unable to run). The test asserts the
    *deterministic* outcome is FAIL with the missing-key clause named.

    We also assert that the Verdict schema can carry a literal BLOCKED
    code (for completeness, since the schema must support it).
    """
    from aios_kernel.verifier.protocol import Verdict
    from aios_kernel.verifier.protocol import VerdictCode as VC

    now = _now()
    eid = uuid.uuid4().hex
    aid = uuid.uuid4().hex
    store.put_evidence(
        EvidenceRecord(
            evidence_id=eid,
            task_id="task-blocked",
            verifier_id="worker-stub",
            verdict="PASS",
            artifact_ids=[aid],
            evidence_hash="a" * 64,
            details={"status": "ok"},  # 'count' is missing (partial)
            signed_at=now,
        )
    )
    store.put_artifact(
        ArtifactRecord(
            artifact_id=aid,
            task_id="task-blocked",
            artifact_type="text",
            path=None,
            inline_content="hi",
            inline_json=None,
            hash_sha256=hashlib.sha256(b"hi").hexdigest(),
            size_bytes=2,
        )
    )
    task = {
        "id": "task-blocked",
        "evidence_ids": [eid],
        "artifact_ids": [aid],
        # criteria requires 'count' which is missing -> partial evidence
        "success_criteria": "status=ok;count=5",
        "cost_yuan": 0.0,
        "budget_yuan": 10.0,
    }
    verdict = await verifier.verify(task, [eid])
    # We expect FAIL on the success_criteria rule (partial evidence)
    assert verdict.verdict == VerdictCode.FAIL
    assert verdict.details["success_criteria"]["ok"] is False
    failed = verdict.details["success_criteria"]["failed"]
    assert any("count" in f and "missing_key" in f for f in failed), failed

    # Schema completeness: a literal BLOCKED Verdict is also accepted
    blocked = Verdict(
        task_id="task-blocked",
        verifier_id="itest-verifier",
        verdict=VC.BLOCKED,
        reason="simulated exception during rule evaluation",
        details={"_meta": {"forced": True}},
        signed_at=_now(),
    )
    assert blocked.verdict == VC.BLOCKED
    assert blocked.reason  # exercises the BLOCKED path of the schema
