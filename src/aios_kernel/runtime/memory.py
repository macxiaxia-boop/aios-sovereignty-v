"""runtime/memory.py - Memory Persistence (R1503-011).

Provides persistent JSONL-backed append-only ledger and a simple state.db
key-value store. This is the runtime-side persistence that the scheduler
+ workers use to survive kernel restarts.

R1503-011 acceptance:
  - MemoryPersistence class
  - append_ledger(event_json) writes events.jsonl (atomic)
  - get_ledger_events(since_ts) reads events
  - state_db (set/get/delete/keys)
  - snapshot + restore
  - Tests ≥ 80% coverage

Co-Authored-By: Claude Code (Agent 4 / Hermes) via AIOS R1503
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("aios_kernel.runtime.memory")


@dataclass
class MemoryPersistence:
    """File-backed ledger + key-value state."""

    ledger_path: Path
    state_path: Path
    _state_cache: dict[str, str] = field(default_factory=dict, init=False)
    _state_loaded: bool = field(default=False, init=False)

    # ----- ledger --------------------------------------------------------

    def append_ledger(self, event: dict) -> None:
        event = dict(event)
        event.setdefault("ts", time.time())
        line = json.dumps(event, ensure_ascii=False, sort_keys=True)
        self._append_atomic(self.ledger_path, line + "\n")

    def read_ledger(self, *, since_ts: float | None = None) -> list[dict]:
        if not self.ledger_path.exists():
            return []
        out: list[dict] = []
        for raw in self.ledger_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                log.warning("malformed ledger line skipped: %r", raw[:200])
                continue
            ts = obj.get("ts")
            if since_ts is None or (isinstance(ts, (int, float)) and ts >= since_ts):
                out.append(obj)
        return out

    @staticmethod
    def _append_atomic(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # open in append mode with O_APPEND (POSIX-atomic on most systems) or
        # fall back to plain append on Windows. fsync to make durable.
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(str(path), flags, 0o644)
        try:
            os.write(fd, content.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    # ----- state ---------------------------------------------------------

    def _ensure_state_loaded(self) -> None:
        if self._state_loaded:
            return
        self._state_loaded = True
        if not self.state_path.exists():
            self._state_cache = {}
            return
        try:
            self._state_cache = json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("state.db corrupted, resetting")
            self._state_cache = {}

    def state_get(self, key: str, default: str | None = None) -> str | None:
        self._ensure_state_loaded()
        return self._state_cache.get(key, default)

    def state_set(self, key: str, value: str) -> None:
        self._ensure_state_loaded()
        self._state_cache[key] = value
        self._flush_state()

    def state_delete(self, key: str) -> bool:
        self._ensure_state_loaded()
        if key in self._state_cache:
            del self._state_cache[key]
            self._flush_state()
            return True
        return False

    def state_keys(self) -> list[str]:
        self._ensure_state_loaded()
        return list(self._state_cache.keys())

    def _flush_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(self.state_path.parent),
            prefix=self.state_path.name + ".",
            suffix=".part",
            delete=False,
        ) as tf:
            json.dump(self._state_cache, tf, sort_keys=True)
            tmp_name = tf.name
        os.replace(tmp_name, self.state_path)

    # ----- snapshot -----------------------------------------------------

    def snapshot(self) -> dict:
        return {"state": dict(self._state_cache)}

    def restore(self, snap: dict) -> None:
        self._state_cache = dict(snap.get("state", {}))
        self._state_loaded = True
        self._flush_state()


__all__ = ["MemoryPersistence"]
