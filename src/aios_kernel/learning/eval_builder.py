"""eval_builder.py - C004 Eval Dataset Builder."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow
from aios_kernel.persistence.models import TraceORM


class EvalCase(Envelope):
    """A single evaluation case (synthetic or from real traces)."""
    query: str
    expected_output: str = ""
    source: str = "synthetic"  # "synthetic" | "real"
    difficulty: str = "medium"  # "easy" | "medium" | "hard"
    evidence_id: Optional[str] = None  # back-link to real


class EvalDatasetBuilder:
    """Build evaluation datasets from real traces or synthetic generation."""

    def __init__(self):
        self._cases: list[EvalCase] = []

    async def from_real(self, traces: list[TraceORM], n: int = 100) -> list[EvalCase]:
        """Extract n cases from real traces."""
        cases = []
        for i, t in enumerate(traces[:n]):
            case = EvalCase(
                id=str(uuid.uuid4()),
                query=str(t.payload)[:200] if isinstance(t.payload, dict) else str(t.id),
                expected_output="success" if "complete" in t.event_type or "pass" in t.event_type else "failure",
                source="real",
                difficulty="medium",
                evidence_id=str(t.id),
            )
            cases.append(case)
        return cases

    async def synthetic(self, n: int = 100) -> list[EvalCase]:
        """Generate n synthetic cases (boundary + common patterns)."""
        cases = []
        patterns = [
            ("test_with_basic_input", "easy", "expected_basic_output"),
            ("test_with_edge_case_empty", "medium", "expected_empty_handling"),
            ("test_with_large_input", "hard", "expected_performance_ok"),
            ("test_with_invalid_input", "medium", "expected_validation_error"),
        ]
        for i in range(n):
            q, diff, exp = patterns[i % len(patterns)]
            case = EvalCase(
                id=str(uuid.uuid4()),
                query=f"{q}_#{i}",
                expected_output=f"{exp}_#{i}",
                source="synthetic",
                difficulty=diff,
                evidence_id=None,
            )
            cases.append(case)
        return cases

    async def merge(self, real: list[EvalCase], synth: list[EvalCase]) -> list[EvalCase]:
        """Merge real and synthetic cases (dedup by query)."""
        seen = set()
        merged = []
        for case in real + synth:
            if case.query not in seen:
                seen.add(case.query)
                merged.append(case)
        return merged


__all__ = ["EvalCase", "EvalDatasetBuilder"]
