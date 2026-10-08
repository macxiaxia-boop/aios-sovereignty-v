"""workers - Worker Adapter layer for AIOS Kernel."""
from .base import HealthReport, HealthStatus, NotRegistered, WorkerAdapter
from .claude_code_adapter import ClaudeCodeAdapter
from .codex_adapter import CodexAdapter
from .hermes_adapter import HermesAdapter
from .openclaw_adapter import OpenClawAdapter
from .registry import WorkerRegistry

__all__ = [
    "HealthReport",
    "HealthStatus",
    "NotRegistered",
    "WorkerAdapter",
    "WorkerRegistry",
    "CodexAdapter",
    "ClaudeCodeAdapter",
    "OpenClawAdapter",
    "HermesAdapter",
]
