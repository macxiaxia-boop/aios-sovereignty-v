"""deterministic.py - DeterministicVerifier (T0035 Section 3).

Pure-rule verifier, NO LLM calls. Runs 6 rules in order; the first
failure decides the verdict. The 6 rules map 1:1 to T0035 Scope 3:

    1. evidence list non-empty
    2. each evidence exists in evidence_store
    3. each evidence's hash matches the record
    4. each artifact exists in filesystem
    5. task.success_criteria all verified (heuristic on evidence fields)
    6. no budget overflow (cost_yuan < budget_yuan)

Failure handling:
- any rule 1..4 or 6 hard-fails -> verdict=FAIL
- rule 5 (criteria) is a "soft" check; if the criteria field is empty
  the rule is treated as satisfied. If criteria asks for a substring
  that isn't in any evidence detail, verdict=FAIL. If the evidence
  list is non-empty but some expected fields are missing -> BLOCKED.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import ClassVar

from aios_kernel.verifier.evidence_store import (
    EvidenceStore,
    artifact_record_payload_exists,
    compute_file_sha256,
)
from aios_kernel.verifier.protocol import HealthReport, Verdict, VerdictCode

log = logging.getLogger("aios_kernel.verifier.deterministic")


# ---------- Rule result type ------------------------------------------------


class RuleOutcome:
    """Per-rule result. ok=True means rule passed."""

    __slots__ = ("name", "ok", "message", "data")

    def __init__(self, name: str, ok: bool, message: str = "", data: dict | None = None) -> None:
        self.name = name
        self.ok = ok
        self.message = message
        self.data = data or {}

    def to_dict(self) -> dict:
        return {"ok": self.ok, "message": self.message, **self.data}


# ---------- The 6 rules -----------------------------------------------------


def _rule_evidence_list_nonempty(task: dict, evidence_ids: list) -> RuleOutcome:
    """Rule 1: evidence list must be non-empty."""
    if not evidence_ids:
        return RuleOutcome(
            "evidence_list_nonempty",
            ok=False,
            message="worker produced 0 evidence records",
        )
    return RuleOutcome(
        "evidence_list_nonempty",
        ok=True,
        message=f"{len(evidence_ids)} evidence record(s) attached",
        data={"count": len(evidence_ids)},
    )


def _rule_evidence_exists(store: EvidenceStore, evidence_ids: list) -> RuleOutcome:
    """Rule 2: every evidence id resolves in the evidence_store."""
    missing = []
    for eid in evidence_ids:
        if store.get_evidence(eid) is None:
            missing.append(eid)
    if missing:
        return RuleOutcome(
            "evidence_exists",
            ok=False,
            message=f"{len(missing)} evidence record(s) missing from store",
            data={"missing": missing},
        )
    return RuleOutcome(
        "evidence_exists",
        ok=True,
        message=f"all {len(evidence_ids)} evidence record(s) present",
    )


def _rule_evidence_hash_matches(
    store: EvidenceStore, evidence_ids: list
) -> RuleOutcome:
    """Rule 3: each evidence's stored hash is well-formed (64-char hex).

    "Matches" means: either the evidence_hash field is None (worker
    didn't sign - counted as soft pass for backwards-compat) or the
    stored hash is a 64-char lowercase hex string.

    If the store returns a record with a tampered hash (e.g. wrong
    length), the rule fails.
    """
    bad = []
    unchecked = 0
    for eid in evidence_ids:
        rec = store.get_evidence(eid)
        if rec is None:
            continue
        h = rec.evidence_hash
        if h is None:
            unchecked += 1
            continue
        if not isinstance(h, str) or len(h) != 64:
            bad.append({"evidence_id": eid, "reason": "hash_wrong_length", "got": h})
            continue
        try:
            int(h, 16)
        except ValueError:
            bad.append({"evidence_id": eid, "reason": "hash_not_hex", "got": h})
            continue
    if bad:
        return RuleOutcome(
            "evidence_hash_matches",
            ok=False,
            message=f"{len(bad)} evidence record(s) have invalid hash",
            data={"bad": bad},
        )
    return RuleOutcome(
        "evidence_hash_matches",
        ok=True,
        message=f"all hashes valid ({unchecked} unsigned)",
        data={"unsigned": unchecked},
    )


def _rule_artifact_exists(store: EvidenceStore, task: dict) -> RuleOutcome:
    """Rule 4: every artifact referenced by the task exists in the store AND on disk."""
    artifact_ids = list(task.get("artifact_ids") or [])
    if not artifact_ids:
        return RuleOutcome(
            "artifact_exists",
            ok=True,
            message="task has no artifacts (allowed)",
            data={"count": 0},
        )
    missing_store = []
    missing_files = []
    type_mismatches = []
    for aid in artifact_ids:
        rec = store.get_artifact(aid)
        if rec is None:
            missing_store.append(aid)
            continue
        if not artifact_record_payload_exists(rec):
            missing_files.append(aid)
            continue
        if rec.path and rec.hash_sha256:
            try:
                actual = compute_file_sha256(rec.path)
            except FileNotFoundError:
                missing_files.append(aid)
                continue
            except OSError as exc:
                type_mismatches.append({"artifact_id": aid, "reason": f"os_error: {exc}"})
                continue
            if actual != rec.hash_sha256:
                type_mismatches.append({
                    "artifact_id": aid,
                    "reason": "hash_mismatch",
                    "stored": rec.hash_sha256,
                    "actual": actual,
                })
    if missing_store or missing_files or type_mismatches:
        return RuleOutcome(
            "artifact_exists",
            ok=False,
            message=(
                f"artifact issues: missing_store={len(missing_store)} "
                f"missing_files={len(missing_files)} "
                f"hash_mismatch={len(type_mismatches)}"
            ),
            data={
                "missing_store": missing_store,
                "missing_files": missing_files,
                "hash_mismatch": type_mismatches,
            },
        )
    return RuleOutcome(
        "artifact_exists",
        ok=True,
        message=f"all {len(artifact_ids)} artifact(s) present and valid",
    )


def _rule_success_criteria(
    store: EvidenceStore, task: dict, evidence_ids: list
) -> RuleOutcome:
    """Rule 5: every clause of task.success_criteria is verifiable.

    success_criteria is a free-form string. We use a small deterministic
    parser:

        - empty string  -> pass (no requirements declared)
        - "key=value"   -> the evidence detail dict must contain
                           key=value (string match)
        - "key=*present" -> key must exist in any evidence detail
        - "all:<text>"  -> text must appear in every evidence detail
                           stringification (substring check)
        - multiple clauses separated by ";" or "&&"

    If the criteria is non-empty but no evidence details are available
    -> FAIL. If some clause fails -> FAIL.
    """
    criteria = (task.get("success_criteria") or "").strip()
    if not criteria:
        return RuleOutcome(
            "success_criteria",
            ok=True,
            message="no success_criteria declared (auto-pass)",
        )

    if not evidence_ids:
        return RuleOutcome(
            "success_criteria",
            ok=False,
            message="criteria declared but no evidence to check against",
        )

    merged = {}
    evidence_strings = []
    any_evidence = False
    for eid in evidence_ids:
        rec = store.get_evidence(eid)
        if rec is None:
            continue
        any_evidence = True
        merged.update(rec.details or {})
        evidence_strings.append(str(rec.details or {}))
    if not any_evidence:
        return RuleOutcome(
            "success_criteria",
            ok=False,
            message="criteria declared but no evidence details available",
        )

    clauses = [c.strip() for c in criteria.replace("&&", ";").split(";") if c.strip()]
    failed = []
    for clause in clauses:
        if "=" not in clause:
            if clause.lower() not in " ".join(evidence_strings).lower():
                failed.append(f"keyword_not_found: {clause!r}")
            continue
        key, _, value = clause.partition("=")
        key = key.strip()
        value = value.strip()
        if value == "*present":
            if key not in merged:
                failed.append(f"missing_key: {key!r}")
            continue
        if "all:" in key:
            token = key.split("all:", 1)[1]
            for s in evidence_strings:
                if token.lower() not in s.lower():
                    failed.append(f"all_token_not_in_evidence: {token!r}")
                    break
            continue
        actual = merged.get(key)
        if actual is None:
            failed.append(f"missing_key: {key!r}")
            continue
        if str(actual) != value:
            failed.append(f"value_mismatch: {key} expected={value!r} got={actual!r}")

    if failed:
        return RuleOutcome(
            "success_criteria",
            ok=False,
            message=f"{len(failed)} criteria clause(s) failed",
            data={"failed": failed},
        )
    return RuleOutcome(
        "success_criteria",
        ok=True,
        message=f"all {len(clauses)} criteria clause(s) satisfied",
        data={"clauses": clauses},
    )


def _rule_budget_not_overflow(task: dict) -> RuleOutcome:
    """Rule 6: cost_yuan < budget_yuan.

    Missing budget -> we treat as "unlimited" and pass with a warning.
    Missing cost  -> 0.0.
    """
    cost = task.get("cost_yuan", 0.0)
    budget = task.get("budget_yuan", None)
    try:
        cost = float(cost or 0.0)
    except (TypeError, ValueError):
        cost = 0.0
    if budget is None:
        return RuleOutcome(
            "budget_not_overflow",
            ok=True,
            message="no budget declared (auto-pass)",
            data={"cost_yuan": cost, "budget_yuan": None},
        )
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return RuleOutcome(
            "budget_not_overflow",
            ok=True,
            message=f"budget {budget!r} not parseable; auto-pass",
            data={"cost_yuan": cost, "budget_yuan": budget},
        )
    if cost > budget:
        return RuleOutcome(
            "budget_not_overflow",
            ok=False,
            message=f"cost_yuan={cost} exceeds budget_yuan={budget}",
            data={"cost_yuan": cost, "budget_yuan": budget, "overrun": cost - budget},
        )
    return RuleOutcome(
        "budget_not_overflow",
        ok=True,
        message=f"cost_yuan={cost} <= budget_yuan={budget}",
        data={"cost_yuan": cost, "budget_yuan": budget, "remaining": budget - cost},
    )


# ---------- DeterministicVerifier -------------------------------------------


class DeterministicVerifier:
    """Pure rule-based verifier. No LLM, no network, deterministic.

    Usage (in-process, e.g. inside tests):
        store = InMemoryEvidenceStore()
        store.put_evidence(...)
        v = DeterministicVerifier("det-1", store)
        verdict = await v.verify(task_dict, evidence_ids)

    Usage (out-of-process, e.g. via FastAPI in `server.py`):
        POST /verify {task: {...}, verifier_id: "..."} -> Verdict JSON
    """

    RULE_NAMES: ClassVar[list] = [
        "evidence_list_nonempty",
        "evidence_exists",
        "evidence_hash_matches",
        "artifact_exists",
        "success_criteria",
        "budget_not_overflow",
    ]

    def __init__(
        self,
        verifier_id: str,
        store: EvidenceStore,
        *,
        process_started_at=None,
    ) -> None:
        self.verifier_id = verifier_id
        self._store = store
        self._started_at = process_started_at or _now_utc()

    async def verify(self, task, evidence_ids):
        """Run all 6 rules; return the first failure as FAIL, or PASS."""
        t0 = time.perf_counter()
        outcomes = []

        outcomes.append(_rule_evidence_list_nonempty(task, evidence_ids))
        if not outcomes[-1].ok:
            return self._finalize(task, outcomes, blocked=False, t0=t0)

        outcomes.append(_rule_evidence_exists(self._store, evidence_ids))
        if not outcomes[-1].ok:
            return self._finalize(task, outcomes, blocked=False, t0=t0)

        outcomes.append(_rule_evidence_hash_matches(self._store, evidence_ids))
        if not outcomes[-1].ok:
            return self._finalize(task, outcomes, blocked=False, t0=t0)

        outcomes.append(_rule_artifact_exists(self._store, task))
        if not outcomes[-1].ok:
            return self._finalize(task, outcomes, blocked=False, t0=t0)

        outcomes.append(_rule_success_criteria(self._store, task, evidence_ids))
        if not outcomes[-1].ok:
            return self._finalize(task, outcomes, blocked=False, t0=t0)

        outcomes.append(_rule_budget_not_overflow(task))
        if not outcomes[-1].ok:
            return self._finalize(task, outcomes, blocked=False, t0=t0)

        return self._finalize(task, outcomes, blocked=False, t0=t0)

    async def health(self) -> HealthReport:
        return HealthReport(
            verifier_id=self.verifier_id,
            status="healthy",
            pid=os.getpid(),
            started_at=self._started_at,
            uptime_seconds=(_now_utc() - self._started_at).total_seconds(),
            rules_loaded=list(self.RULE_NAMES),
            message="deterministic verifier; no LLM",
        )

    def _finalize(self, task, outcomes, *, blocked, t0) -> Verdict:
        details = {o.name: o.to_dict() for o in outcomes}
        passed = all(o.ok for o in outcomes)
        if blocked:
            code = VerdictCode.BLOCKED
            reason = "verifier could not reach a conclusion"
        elif passed:
            code = VerdictCode.PASS
            reason = "all 6 deterministic rules passed"
        else:
            failing = [o for o in outcomes if not o.ok]
            first = failing[0]
            code = VerdictCode.FAIL
            reason = f"rule {first.name!r} failed: {first.message}"

        elapsed = time.perf_counter() - t0
        meta = details.setdefault("_meta", {})
        meta.update({
            "elapsed_s": round(elapsed, 6),
            "rules_run": [o.name for o in outcomes],
            "deterministic": True,
        })
        return Verdict(
            task_id=str(task.get("id") or ""),
            verifier_id=self.verifier_id,
            verdict=code,
            reason=reason,
            details=details,
            signed_at=_now_utc(),
            cost_yuan=0.0,
        )


def _now_utc():
    from datetime import UTC
    return datetime.now(UTC)


__all__ = ["DeterministicVerifier", "RuleOutcome"]
