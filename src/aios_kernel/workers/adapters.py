"""adapters.py - Adapters framework helpers (R1503-003).

This module provides:
  - adapter wrapping helpers (e.g. `cli_subprocess_adapter` to wrap any CLI
    binary as a WorkerAdapter)
  - HTTP-based adapter (`http_adapter` to wrap a JSON-over-HTTP service)
  - the canonical 4-Agent adapter registration for AIOS

R1503-003 acceptance:
  - Generic Adapter factory that lets a third party plug a new worker in
    <20 lines of code.
  - Built-in CLI and HTTP adapter templates.
  - Pre-wired 4-Agent registration matches the R1503-4AGENT spec.

Co-Authored-By: Claude Code <noreply@anthropic.com>
"""
from __future__ import annotations

import asyncio
import logging
import os
import shlex
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from aios_kernel.domain.artifact import Artifact, ArtifactType
from aios_kernel.workers.base import HealthReport, HealthStatus, WorkerAdapter

log = logging.getLogger("aios_kernel.workers.adapters")


@runtime_checkable
class CLIExecutable(Protocol):
    """Anything with .run(cmd, env) -> (stdout, stderr, exit_code)."""

    def run(self, cmd: list[str], env: dict[str, str]) -> tuple[str, str, int]: ...


class SubprocessRunner:
    """Default CLIExecutable using asyncio.create_subprocess_exec."""

    async def run(self, cmd: list[str], env: dict[str, str]) -> tuple[str, str, int]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ.copy(), **env},
        )
        stdout_b, stderr_b = await proc.communicate()
        return (
            stdout_b.decode(errors="replace"),
            stderr_b.decode(errors="replace"),
            proc.returncode if proc.returncode is not None else -1,
        )


def cli_subprocess_adapter(
    worker_id: str,
    *,
    binary: str,
    arg_template: str = "{task_input_json}",
    timeout_s: float = 60.0,
    runner: CLIExecutable | None = None,
    healthy_exit_codes: tuple[int, ...] = (0,),
) -> WorkerAdapter:
    """Wrap a CLI binary as a WorkerAdapter.

    Example:
        adapter = cli_subprocess_adapter(
            "claude-code-cli",
            binary="claude",
            arg_template="--prompt {task_title}",
            timeout_s=30.0,
        )
    """
    runner = runner or _SyncRunnerAdapter()

    class _CLIAdapter:
        def __init__(self) -> None:
            self.worker_id = worker_id
            self._binary = binary
            self._arg_template = arg_template
            self._timeout_s = timeout_s
            self._runner = runner

        async def execute(self, task):
            payload = {
                "task_id": str(task.id),
                "task_title": task.title,
                "task_description": task.description or "",
                "task_input": task.input_payload,
            }
            rendered_args = _render_arg_template(
                self._arg_template, payload,
            )
            cmd = [self._binary, *shlex.split(rendered_args)]
            try:
                stdout, stderr, code = await asyncio.wait_for(
                    self._runner.run(cmd, env={}),
                    timeout=self._timeout_s,
                )
            except TimeoutError:
                return Artifact(
                    task_id=task.id,
                    artifact_type=ArtifactType.ERROR,
                    label="cli_timeout",
                    inline_json={
                        "worker": worker_id,
                        "binary": self._binary,
                        "timeout_s": self._timeout_s,
                    },
                )
            return Artifact(
                task_id=task.id,
                artifact_type=ArtifactType.CUSTOM,
                label="cli_result",
                inline_json={
                    "worker": worker_id,
                    "exit_code": code,
                    "stdout": stdout[:8192],
                    "stderr": stderr[:4096],
                    "healthy": code in healthy_exit_codes,
                },
            )

        async def cancel(self, task_id):
            log.info("cli_subprocess_adapter %s: cancel %s (no-op)", worker_id, task_id)

        async def health(self):
            return HealthReport(
                worker_id=worker_id,
                status=HealthStatus.HEALTHY,
                last_check_at=datetime.now(UTC),
                metadata={"kind": "cli", "binary": binary},
            )

        async def warmup(self):
            log.info("cli_subprocess_adapter %s: warmup (no-op)", worker_id)

        async def shutdown(self):
            log.info("cli_subprocess_adapter %s: shutdown (no-op)", worker_id)

    return _CLIAdapter()


class _SyncRunnerAdapter:
    """Adapter from sync runner to async signature."""

    def __init__(self) -> None:
        self._inner = SubprocessRunner()

    async def run(self, cmd, env):
        return await self._inner.run(cmd, env)


def _render_arg_template(template: str, payload: dict[str, Any]) -> str:
    """Render a simple {key} template; raises KeyError on missing keys."""
    try:
        return template.format(**payload)
    except KeyError as exc:
        raise ValueError(f"arg_template missing key {exc.args[0]!r}")


# ----- HTTP adapter template ----------------------------------------------


def http_adapter(
    worker_id: str,
    *,
    base_url: str,
    submit_path: str = "/tasks",
    status_path: str = "/tasks/{task_id}",
    timeout_s: float = 60.0,
    auth_token: str | None = None,
) -> WorkerAdapter:
    """Wrap a JSON-over-HTTP service as a WorkerAdapter (httpx stub)."""

    class _HTTPAdapter:
        def __init__(self) -> None:
            self.worker_id = worker_id
            self._base_url = base_url
            self._submit_path = submit_path
            self._status_path = status_path
            self._timeout_s = timeout_s
            self._auth_token = auth_token

        async def execute(self, task):
            payload = {
                "task_id": str(task.id),
                "title": task.title,
                "input": task.input_payload,
            }
            # NOTE: this is a STUB adapter. Real implementation requires `httpx`.
            # Until httpx is wired, we just synthesize a healthy artifact so
            # the scheduler + registry keep working in dev/test.
            return Artifact(
                task_id=task.id,
                artifact_type=ArtifactType.CUSTOM,
                label="http_stub",
                inline_json={
                    "worker": worker_id,
                    "base_url": self._base_url,
                    "submit_path": self._submit_path,
                    "submitted_payload": payload,
                    "stub": True,
                },
            )

        async def cancel(self, task_id):
            log.info("http_adapter %s: cancel %s (no-op)", worker_id, task_id)

        async def health(self):
            return HealthReport(
                worker_id=worker_id,
                status=HealthStatus.HEALTHY,
                last_check_at=datetime.now(UTC),
                metadata={"kind": "http", "base_url": base_url},
            )

        async def warmup(self):
            log.info("http_adapter %s: warmup (no-op)", worker_id)

        async def shutdown(self):
            log.info("http_adapter %s: shutdown (no-op)", worker_id)

    return _HTTPAdapter()


# ----- 4-Agent canonical registration -----------------------------------


def register_four_agent_team(
    registry: Any,
    *,
    claude_binary: str = "claude",
    codex_binary: str = "codex",
    openclaw_base_url: str = "http://localhost:18792",
    hermes_base_url: str = "http://localhost:18803",
) -> None:
    """Register the canonical 4-Agent WorkerAdapter team (R1503 §2).

    Idempotent. Adapter worker_ids are deterministic.
    """
    from aios_kernel.workers.claude_code_adapter import ClaudeCodeAdapter
    from aios_kernel.workers.codex_adapter import CodexAdapter
    from aios_kernel.workers.hermes_adapter import HermesAdapter
    from aios_kernel.workers.openclaw_adapter import OpenClawAdapter

    try:
        registry.register(ClaudeCodeAdapter())
    except ValueError:
        pass
    try:
        registry.register(CodexAdapter())
    except ValueError:
        pass
    try:
        registry.register(OpenClawAdapter())
    except ValueError:
        pass
    try:
        registry.register(HermesAdapter())
    except ValueError:
        pass


__all__ = [
    "cli_subprocess_adapter",
    "http_adapter",
    "register_four_agent_team",
    "SubprocessRunner",
    "CLIExecutable",
]
