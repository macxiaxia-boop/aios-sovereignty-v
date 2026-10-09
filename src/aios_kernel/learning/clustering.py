"""Deterministic failure-pattern clustering for AIOS Phase F (F004)."""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class FailureTrace:
    """A single normalized failure trace accepted by :class:`FailurePatternMerger`."""

    id: str
    error_message: str
    error_type: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""  # ISO 8601


@dataclass(slots=True)
class FailureCluster:
    """A deterministic aggregate of failures sharing one normalized message."""

    cluster_id: str
    root_cause: str
    error_type: str
    affected_trace_ids: list[str]
    occurrence_count: int
    severity_score: float
    first_seen: str
    last_seen: str
    recommended_fix: str
    sample_error_messages: list[str]


class FailurePatternMerger:
    """Merge noisy :class:`FailureTrace` records without an LLM dependency."""

    _WINDOWS_PATH = re.compile(r"(?i)\b[A-Z]:\\(?:[^\\\s]+\\)*[^\\\s]*")
    _UNC_PATH = re.compile(r"(?i)\\\\[^\\\s]+(?:\\[^\\\s]+)+")
    _TIMESTAMP = re.compile(
        r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
    )
    _UUID = re.compile(
        r"(?i)\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b"
    )
    _IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
    _HEX = re.compile(r"(?i)\b[0-9a-f]{12,}\b")

    def __init__(self, eps: float = 0.15, min_samples: int = 2):
        if not 0 < eps <= 1:
            raise ValueError("eps must be in the (0, 1] range")
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        self.eps = eps
        self.min_samples = min_samples

    @staticmethod
    def _timestamp_key(value: str) -> tuple[int, float, str]:
        """Sort valid ISO timestamps chronologically while tolerating bad input."""
        if not value:
            return (0, 0.0, "")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return (1, 0.0, value)
        return (2, parsed.timestamp(), value)

    def _normalize(self, error_message: str) -> str:
        """Remove volatile values and canonicalize whitespace/case."""
        if not isinstance(error_message, str):
            error_message = str(error_message)
        normalized = error_message.strip()
        normalized = self._WINDOWS_PATH.sub("<PATH>", normalized)
        normalized = self._UNC_PATH.sub("<PATH>", normalized)
        normalized = self._TIMESTAMP.sub("<TS>", normalized)
        normalized = self._UUID.sub("<UUID>", normalized)
        normalized = self._IP.sub("<IP>", normalized)
        normalized = self._HEX.sub("<HEX>", normalized)
        normalized = self._NUMBER.sub("<NUM>", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.casefold()

    def _hash(self, normalized: str) -> str:
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def _severity(self, occurrence: int, impact: float = 1.0) -> float:
        return min(10.0, max(0, occurrence) * max(0.0, impact))

    @staticmethod
    def _root_cause(error_type: str, normalized_msg: str) -> str:
        error_type_l = error_type.casefold()
        message_l = normalized_msg.casefold()
        rules = (
            (("permissionerror", "permission denied", "permission"), "permission_denied"),
            (("filenotfounderror", "no such file", "file missing"), "file_missing"),
            (("timeouterror", "timeout", "timed out"), "timeout"),
            (("connectionerror", "connection", "unreachable"), "network_unavailable"),
            (("validationerror", "validation", "invalid input"), "input_invalid"),
        )
        for needles, root_cause in rules:
            if any(needle in error_type_l or needle in message_l for needle in needles):
                return root_cause
        return f"unknown:{error_type or 'unspecified'}"

    @staticmethod
    def _recommend_fix(root_cause: str) -> str:
        fixes = {
            "permission_denied": "Check file/dir permissions; ensure process runs as required user",
            "file_missing": "Verify file exists at expected path; create if needed",
            "timeout": "Increase timeout; check if service is overloaded",
            "network_unavailable": "Check connectivity; verify service is reachable",
            "input_invalid": "Validate input schema; add pre-check",
        }
        return fixes.get(root_cause, "Investigate manually; add specific check")

    @staticmethod
    def _impact(trace: FailureTrace) -> float:
        raw = trace.context.get("impact", 1.0)
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            return 1.0

    def merge(self, failures: Iterable[FailureTrace]) -> list[FailureCluster]:
        """Normalize and hash traces, then return clusters sorted by severity."""
        groups: dict[str, list[tuple[FailureTrace, str]]] = defaultdict(list)
        for failure in failures:
            if not isinstance(failure, FailureTrace):
                raise TypeError("failures must contain FailureTrace instances")
            normalized = self._normalize(failure.error_message)
            groups[self._hash(normalized)].append((failure, normalized))

        clusters: list[FailureCluster] = []
        for cluster_id, items in groups.items():
            first = items[0][0]
            root_cause = self._root_cause(first.error_type, items[0][1])
            timestamps = sorted((item[0].timestamp for item in items), key=self._timestamp_key)
            total_impact = sum(self._impact(item[0]) for item in items)
            average_impact = total_impact / len(items)
            clusters.append(
                FailureCluster(
                    cluster_id=cluster_id,
                    root_cause=root_cause,
                    error_type=first.error_type,
                    affected_trace_ids=[item[0].id for item in items],
                    occurrence_count=len(items),
                    severity_score=self._severity(len(items), average_impact),
                    first_seen=timestamps[0],
                    last_seen=timestamps[-1],
                    recommended_fix=self._recommend_fix(root_cause),
                    sample_error_messages=[item[0].error_message for item in items[:5]],
                )
            )
        clusters.sort(key=lambda cluster: (-cluster.severity_score, -cluster.occurrence_count, cluster.cluster_id))
        return clusters


def merge_rate(original_count: int, clusters: list[FailureCluster]) -> float:
    """Return ``1 - cluster_count / original_count`` in the closed range [0, 1]."""
    if original_count <= 0:
        return 0.0
    rate = 1.0 - (len(clusters) / original_count)
    return min(1.0, max(0.0, rate))


__all__ = ["FailureTrace", "FailureCluster", "FailurePatternMerger", "merge_rate"]

