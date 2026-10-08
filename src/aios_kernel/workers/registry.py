"""registry.py - Worker Adapter registry + routing."""
from __future__ import annotations
from typing import Iterable

from aios_kernel.workers.base import NotRegistered, WorkerAdapter


class WorkerRegistry:
    def __init__(self):
        self._adapters: dict[str, WorkerAdapter] = {}
        self._rr_counter = 0

    def register(self, adapter: WorkerAdapter) -> None:
        self._adapters[adapter.worker_id] = adapter

    def unregister(self, worker_id: str) -> None:
        self._adapters.pop(worker_id, None)

    def get(self, worker_id: str) -> WorkerAdapter:
        if worker_id not in self._adapters:
            raise NotRegistered(f"worker {worker_id} not registered")
        return self._adapters[worker_id]

    def list_ids(self) -> list[str]:
        return list(self._adapters.keys())

    def route(self, task) -> WorkerAdapter:
        # 1. preferred worker
        preferred = getattr(task, "worker", None)
        if preferred and preferred in self._adapters:
            return self._adapters[preferred]
        # 2. by task type
        TYPE_ROUTING = {
            "tofu": "codex-adapter",
            "code": "claude-code-adapter",
            "shell": "openclaw-adapter",
            "review": "hermes-adapter",
            "file_summary": "codex-adapter",
            "string_format": "codex-adapter",
            "math_calc": "claude-code-adapter",
            "env_probe": "openclaw-adapter",
            "cross_worker": "hermes-adapter",
            "custom": "codex-adapter",
        }
        task_type = getattr(task, "type", None)
        type_val = getattr(task_type, "value", str(task_type)) if task_type else None
        if type_val:
            mapped = TYPE_ROUTING.get(type_val)
            if mapped and mapped in self._adapters:
                return self._adapters[mapped]
        # 3. round-robin
        ids = self.list_ids()
        if not ids:
            raise NotRegistered("no workers registered")
        idx = self._rr_counter % len(ids)
        self._rr_counter += 1
        return self._adapters[ids[idx]]
