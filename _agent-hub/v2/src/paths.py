# v2/src/paths.py — single source of truth for v2 paths.
from __future__ import annotations

import os
from pathlib import Path

V2_ROOT = Path(os.environ.get("AIOS_V2_ROOT", r"D:\AIOS\_agent-hub\v2")).resolve()

SCHEMAS = V2_ROOT / "schemas"
AGENTS_JSON = V2_ROOT / "agents" / "agents.json"
PROTOCOL_V1 = V2_ROOT / "protocols" / "v1.md"

MESSAGES = V2_ROOT / "messages"
INBOX = MESSAGES / "inbox"
OUTBOX = MESSAGES / "outbox"
DEADLETTER = MESSAGES / "deadletter"

TASKS_DIR = V2_ROOT / "tasks"
RUNS_DIR = V2_ROOT / "runs"
LOGS_DIR = V2_ROOT / "logs"
EVENTS_LOG = LOGS_DIR / "events.ndjson"
STATE_FILE = V2_ROOT / "state" / "state.json"
REPORTS_DIR = V2_ROOT / "reports"


def ensure_dirs() -> None:
    """Create the v2 directory tree if missing. Idempotent."""
    for p in (INBOX, OUTBOX, DEADLETTER, TASKS_DIR, RUNS_DIR, LOGS_DIR,
              STATE_FILE.parent, REPORTS_DIR):
        p.mkdir(parents=True, exist_ok=True)
    if not EVENTS_LOG.exists():
        EVENTS_LOG.touch()


def v2_root() -> Path:
    return V2_ROOT