"""P10 opt-in SQLite dispatch journal for the EXISTING AIOSScheduler.

This is not a replacement workflow engine. It provides durable submission,
atomic cross-process claims and fencing. Recovery intentionally requeues ONLY
read-only CloudTech preflight; interrupted effects are quarantined.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from aios_kernel.domain.task import Task


class DurableDispatchStore:
    """Each operation has its own short BEGIN IMMEDIATE transaction."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS dispatch_runs (
                    run_id TEXT PRIMARY KEY,
                    task_json TEXT NOT NULL,
                    tenant_id TEXT,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner TEXT,
                    fence INTEGER NOT NULL DEFAULT 0,
                    expires_at REAL NOT NULL DEFAULT 0,
                    artifact_json TEXT,
                    updated_at REAL NOT NULL
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_dispatch_claim
                ON dispatch_runs(status, priority, updated_at)
            """)

    @contextmanager
    def _connect(self):
        # The sqlite3.Connection context manager alone does not close handles.
        # Release the Windows file lock promptly after every short operation.
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA busy_timeout=15000")
            db.execute("PRAGMA journal_mode=WAL")
            yield db
        finally:
            db.close()

    def enqueue(self, run_id: str, task: Task, priority: str) -> bool:
        tenant_id = task.input_payload.get("tenant_id")
        if tenant_id is not None and not isinstance(tenant_id, str):
            raise ValueError("tenant_id must be a string")
        encoded_task = task.model_dump_json()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            result = db.execute(
                """INSERT OR IGNORE INTO dispatch_runs
                (run_id, task_json, tenant_id, priority, status, updated_at)
                VALUES (?, ?, ?, ?, 'queued', ?)""",
                (run_id, encoded_task, tenant_id, priority, time.time()),
            )
            if result.rowcount == 0:
                existing = db.execute(
                    "SELECT task_json, tenant_id, priority FROM dispatch_runs WHERE run_id=?",
                    (run_id,),
                ).fetchone()
                if (existing is None or existing["task_json"] != encoded_task
                        or existing["tenant_id"] != tenant_id
                        or existing["priority"] != priority):
                    raise ValueError(
                        "conflicting durable dispatch run_id request; original preserved"
                    )
            db.commit()
            return result.rowcount == 1

    def claim(self, owner: str, *, ttl_s: float = 300) -> dict[str, Any] | None:
        if ttl_s <= 0 or not owner:
            raise ValueError("invalid dispatch lease parameters")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT * FROM dispatch_runs WHERE status='queued'
                ORDER BY CASE priority WHEN 'P0' THEN 0
                            WHEN 'P1' THEN 1 ELSE 2 END, updated_at ASC
                LIMIT 1"""
            ).fetchone()
            if row is None:
                db.commit()
                return None
            fence = row["fence"] + 1
            db.execute(
                """UPDATE dispatch_runs SET status='running', owner=?,
                fence=?, expires_at=?, updated_at=? WHERE run_id=?""",
                (owner, fence, time.time() + ttl_s, time.time(), row["run_id"]),
            )
            db.commit()
            return {
                "run_id": row["run_id"],
                "task": Task.model_validate_json(row["task_json"]),
                "priority": row["priority"],
                "owner": owner,
                "fence": fence,
            }

    def renew(self, run_id: str, owner: str, fence: int, *, ttl_s: float) -> bool:
        with self._connect() as db:
            result = db.execute(
                """UPDATE dispatch_runs SET expires_at=?, updated_at=?
                WHERE run_id=? AND owner=? AND fence=? AND status='running'
                AND expires_at>?""",
                (time.time() + ttl_s, time.time(), run_id, owner, fence, time.time()),
            )
            return result.rowcount == 1

    def finish(
        self, run_id: str, owner: str, fence: int, *,
        status: str, artifact: dict[str, Any] | None = None,
    ) -> bool:
        if status not in {"completed", "failed", "blocked_uncertain"}:
            raise ValueError("invalid terminal dispatch state")
        with self._connect() as db:
            result = db.execute(
                """UPDATE dispatch_runs SET status=?, artifact_json=?,
                updated_at=?, owner=NULL, expires_at=0
                WHERE run_id=? AND owner=? AND fence=? AND status='running'
                AND expires_at>?""",
                (
                    status, json.dumps(artifact, ensure_ascii=False, default=str)
                    if artifact is not None else None,
                    time.time(), run_id, owner, fence, time.time(),
                ),
            )
            return result.rowcount == 1

    @staticmethod
    def _safe_to_replay(task: Task) -> bool:
        return (
            task.worker == "cloudtech-v4-adapter"
            and task.input_payload.get("action") == "preflight"
        )

    def recover_expired(self, *, now: float | None = None) -> dict[str, int]:
        """Expired in-flight work MUST NOT blindly repeat external effects."""
        current = time.time() if now is None else now
        recovered = 0
        quarantined = 0
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                """SELECT run_id, task_json FROM dispatch_runs
                WHERE status='running' AND expires_at<=?""", (current,)
            ).fetchall()
            for row in rows:
                task = Task.model_validate_json(row["task_json"])
                safe = self._safe_to_replay(task)
                db.execute(
                    """UPDATE dispatch_runs
                    SET status=?, owner=NULL, expires_at=0, updated_at=?
                    WHERE run_id=? AND status='running' AND expires_at<=?""",
                    (
                        "queued" if safe else "blocked_uncertain",
                        current, row["run_id"], current,
                    ),
                )
                if safe:
                    recovered += 1
                else:
                    quarantined += 1
            db.commit()
        return {"requeued_readonly": recovered, "blocked_uncertain": quarantined}

    def status(self, run_id: str) -> str:
        """State-only query, without leaking the private task or artifact."""
        with self._connect() as db:
            row = db.execute(
                "SELECT status FROM dispatch_runs WHERE run_id=?", (run_id,)
            ).fetchone()
        return row["status"] if row else "unknown"

    def get(self, run_id: str, *, tenant_id: str | None = None) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM dispatch_runs WHERE run_id=?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        # Internal callers may omit the tenant to inspect a legacy run, but
        # authenticated tenant-scoped HTTP must never read a tenantless row.
        if tenant_id is not None and row["tenant_id"] != tenant_id:
            return None
        if tenant_id is None and row["tenant_id"] is not None:
            return None
        return {
            "run_id": row["run_id"],
            "state": row["status"],
            "tenant_id": row["tenant_id"],
            "fence": row["fence"],
            "artifact": json.loads(row["artifact_json"])
            if row["artifact_json"] is not None else None,
            "priority": row["priority"],
        }
