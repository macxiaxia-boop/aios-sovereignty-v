"""aios_kernel.governance.model_policy — Model Policy reconciler (AIOS-SOVEREIGNTY-V).

Implements:
- Snapshot loader for ModelPolicy v1 YAML
- Base adapter interface
- 4 concrete adapters (Codex / Claude Code / OpenClaw / Hermes)
- Reconciler coordinator
- CLI entry point (`python -m aios_kernel.governance.model_policy.reconciler`)

Backed by:
- model-policy.v1.yaml in D:\\AIOS\\kernel\\etc\\sovereignty\\
- ed25519 signed by codex_supervisor
- OpenClaw modelPolicyAllowlist migration anchor

Phase F reuse:
- DecisionService (aios_kernel.domain.services.decision_service) — audit trail
- GoalGuard (aios_kernel.governance.goal_guard) — policy changes are goals
- FailurePatternMerger (aios_kernel.learning.clustering) — drift cluster
"""
from __future__ import annotations

from .snapshot import PolicySnapshot, load_policy, verify_signature, sign_yaml
from .adapter_base import ModelPolicyAdapter, DriftReport
from .reconciler import reconcile, main

__all__ = [
    "PolicySnapshot",
    "load_policy",
    "verify_signature",
    "sign_yaml",
    "ModelPolicyAdapter",
    "DriftReport",
    "reconcile",
    "main",
]
