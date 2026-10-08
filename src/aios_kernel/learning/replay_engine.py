"""replay_engine.py - C005 Replay Engine."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope


class ReplayResult(Envelope):
    """Result of replaying a historical run against a new kernel."""
    historical_run_id: str
    status: str = "pending"  # "success" | "failure" | "drift"
    duration_ms: int = 0
    outputs: dict = Field(default_factory=dict)
    diffs_from_expected: list[str] = Field(default_factory=list)


class ReplayEngine:
    """Replay historical workflow runs against a new kernel."""

    def __init__(self):
        self._results: list[ReplayResult] = []

    async def replay(
        self,
        historical_run: dict,
        new_kernel_outputs: dict,
    ) -> ReplayResult:
        """Replay historical_run using new_kernel_outputs and return diff."""
        start = datetime.now(UTC)
        expected_outputs = historical_run.get("outputs", {})
        diffs = self.diff_detect(expected_outputs, new_kernel_outputs)
        status = "success" if not diffs else ("drift" if new_kernel_outputs else "failure")
        result = ReplayResult(
            id=str(uuid.uuid4()),
            historical_run_id=historical_run.get("run_id", "unknown"),
            status=status,
            duration_ms=int((datetime.now(UTC) - start).total_seconds() * 1000),
            outputs=new_kernel_outputs,
            diffs_from_expected=diffs,
        )
        self._results.append(result)
        return result

    def diff_detect(self, expected: dict, actual: dict) -> list[str]:
        """Return list of differences between expected and actual."""
        diffs = []
        all_keys = set(expected.keys()) | set(actual.keys())
        for k in sorted(all_keys):
            e = expected.get(k)
            a = actual.get(k)
            if e != a:
                diffs.append(f"{k}: expected={e!r}, actual={a!r}")
        return diffs


__all__ = ["ReplayResult", "ReplayEngine"]
