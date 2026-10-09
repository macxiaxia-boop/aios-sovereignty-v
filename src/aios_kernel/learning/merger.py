"""Convert failure clusters into GoalContract failure modes (F004)."""
from __future__ import annotations

from aios_kernel.domain.goal import FailureMode
from aios_kernel.learning.clustering import FailureCluster


def clusters_to_failure_modes(
    clusters: list[FailureCluster], min_occurrence: int = 3
) -> list[FailureMode]:
    """Convert sufficiently frequent clusters into validated FailureMode models."""
    if min_occurrence < 1:
        raise ValueError("min_occurrence must be at least 1")
    modes: list[FailureMode] = []
    for cluster in clusters:
        if cluster.occurrence_count < min_occurrence:
            continue
        modes.append(
            FailureMode(
                description=(
                    f"[{cluster.root_cause}] {cluster.error_type} "
                    f"(occurs {cluster.occurrence_count}x)"
                ),
                detection=(
                    f"error_type={cluster.error_type}; normalized_hash={cluster.cluster_id[:8]}"
                ),
                indicator=cluster.sample_error_messages[0] if cluster.sample_error_messages else None,
            )
        )
    return modes


def suggest_preserve_capabilities(clusters: list[FailureCluster]) -> list[str]:
    """Return stable capabilities that must survive changes addressing failures."""
    # F004 does not infer arbitrary capabilities from free-form error text.
    # It returns the Phase F invariants only; no LLM or mutable configuration is used.
    return [
        "verifier/deterministic.py (don't touch)",
        "v2 consumer main loop (don't refactor)",
        "AGENTS.md SSOT",
    ]


__all__ = ["clusters_to_failure_modes", "suggest_preserve_capabilities"]
