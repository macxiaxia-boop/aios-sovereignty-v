# v2/src/supervisor.py — periodic watcher: reap expired tasks, build snapshot.
from __future__ import annotations

import json
import sys
import time
from typing import Optional

from .paths import EVENTS_LOG, ensure_dirs
from .probes import probe_all
from .state_machine import (build_state_snapshot, reap_expired, save_state_snapshot,
                            list_tasks, _log_event)


def tick() -> dict:
    """One supervisor tick: reap + snapshot."""
    ensure_dirs()
    reaped = reap_expired(actor="supervisor")
    snapshot = build_state_snapshot()
    save_state_snapshot(snapshot)
    return {"reaped": reaped, "snapshot_tasks": len(snapshot["tasks"]),
            "snapshot_counters": snapshot["counters"]}


def watch(interval_s: float = 5.0, max_ticks: Optional[int] = None) -> None:
    i = 0
    while True:
        result = tick()
        print(json.dumps(result, ensure_ascii=False), flush=True)
        i += 1
        if max_ticks is not None and i >= max_ticks:
            break
        time.sleep(interval_s)


if __name__ == "__main__":
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    watch(interval_s=interval)