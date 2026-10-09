"""crash_injector.py - T0037 Crash Recovery test helper.

Wraps subprocess.Popen to spawn the kernel worker (see
``_kernel_worker.py``) and provides 5 primitives:

  - start_kernel(db_url, mode, config) -> KernelProcess
  - kill_n9(process)                     -> None  (taskkill /F /PID on Win,
                                                   os.kill SIGKILL on Posix)
  - kill_terminate(process)              -> None  (SIGTERM)
  - restart(process, *, mode, config)    -> KernelProcess
  - verify_state(db_url, expected)       -> dict

Windows uses ``taskkill /F /PID`` because Python on Windows does not
have a portable SIGKILL (os.kill with SIGKILL raises ``ValueError`` on
Win). taskkill /F is the documented equivalent.

The injector is process-oriented (one Python subprocess = one kernel
process) so the kill is a real OS-level kill. This matches the spec:
"Windows: 用 subprocess.Popen + taskkill /F /PID 模拟 SIGKILL".

Test isolation:
  - Each test creates its own sqlite file (via tmp_db_url fixture)
  - Each subprocess writes to a unique result file under a tmp dir
  - After the test, the result files and DB are cleaned up

Concurrency note:
  - We do NOT use asyncio.subprocess here because:
    a) We want true OS-level process kill
    b) Tests need synchronous "start, then wait, then kill" semantics
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------- paths ----------------------------------------------------------

_THIS = Path(__file__).resolve()
_INTEGRATION_DIR = _THIS.parent
_KERNEL_ROOT = _INTEGRATION_DIR.parent.parent  # tests/integration/crash_injector.py -> kernel/
_WORKER_SCRIPT = _INTEGRATION_DIR / "_kernel_worker.py"
_VENV_PY = _KERNEL_ROOT / ".venv" / "Scripts" / "python.exe"


def _python_executable() -> str:
    """Return the python executable to use inside the worker subprocess.

    Prefer the kernel .venv so imports resolve; fall back to current
    interpreter (useful for CI runners that pre-set up sys.path).
    """
    if _VENV_PY.exists():
        return str(_VENV_PY)
    return sys.executable


# ---------- KernelProcess value object -------------------------------------


@dataclass
class KernelProcess:
    """A handle to a spawned kernel subprocess."""

    proc: subprocess.Popen
    pid: int
    db_url: str
    mode: str
    config: dict
    result_path: Path
    marker_path: Path | None = None
    started_at: float = field(default_factory=time.time)
    log_path: Path | None = None

    @property
    def is_alive(self) -> bool:
        return self.proc.poll() is None

    @property
    def returncode(self) -> int | None:
        return self.proc.poll()

    def read_result(self, timeout_s: float = 5.0) -> dict | None:
        """Wait for the worker to write result_path, then read+parse it.

        Returns None if the file is not written within timeout (worker was
        killed before it could write).
        """
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self.result_path.exists():
                try:
                    return json.loads(self.result_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            time.sleep(0.05)
        return None

    def marker_reached(self) -> bool:
        """Did the worker reach its crash hook marker before being killed?"""
        return self.marker_path is not None and self.marker_path.exists()


# ---------- CrashInjector --------------------------------------------------


class CrashInjector:
    """Spawn / kill / restart AIOS kernel subprocess for crash tests.

    Usage:
        inj = CrashInjector()
        proc = inj.start_kernel(db_url="sqlite+aiosqlite:///./x.db",
                                mode="workflow_run",
                                config={"run_id": "r1",
                                        "crash_hook": "crash_after_step_a"})
        inj.wait_for_marker(proc, timeout_s=3.0)
        inj.kill_n9(proc)
        state = inj.verify_state(db_url, expected_run_id="r1")
    """

    def __init__(self, *, default_timeout_s: float = 10.0):
        self.default_timeout_s = default_timeout_s
        self._spawned: list[KernelProcess] = []

    # -- 5-method surface ---------------------------------------------------

    def start_kernel(
        self,
        db_url: str,
        *,
        mode: str,
        config: dict | None = None,
        result_dir: Path | None = None,
        log_dir: Path | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> KernelProcess:
        """Spawn the kernel worker subprocess. Returns a handle."""
        cfg = dict(config or {})
        cfg.setdefault("marker_path", None)

        # result dir
        if result_dir is None:
            result_dir = Path(os.environ.get("TEMP", ".")) / "aios_cr_results"
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / f"result_{os.getpid()}_{time.time_ns()}.json"

        # marker path (auto-create if a crash hook is configured)
        marker_str = cfg.get("marker_path")
        marker_path = Path(marker_str) if marker_str else None
        if marker_path is None and cfg.get("crash_hook") not in (None, "none", ""):
            marker_path = result_path.with_suffix(".marker")
            cfg["marker_path"] = str(marker_path)

        # log dir
        if log_dir is None:
            log_dir = result_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"worker_{os.getpid()}_{time.time_ns()}.log"
        log_fp = open(log_path, "w", encoding="utf-8")

        args = [
            _python_executable(),
            str(_WORKER_SCRIPT),
            "--db-url", db_url,
            "--mode", mode,
            "--config", json.dumps(cfg),
            "--result-path", str(result_path),
        ]

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        if extra_env:
            env.update(extra_env)

        kwargs: dict[str, Any] = {
            "stdout": log_fp,
            "stderr": subprocess.STDOUT,
            "env": env,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen(args, **kwargs)
        kp = KernelProcess(
            proc=proc,
            pid=proc.pid,
            db_url=db_url,
            mode=mode,
            config=cfg,
            result_path=result_path,
            marker_path=marker_path,
            log_path=log_path,
        )
        self._spawned.append(kp)
        return kp

    def kill_n9(self, kp: KernelProcess, *, timeout_s: float = 5.0) -> None:
        """SIGKILL equivalent: taskkill /F /PID on Windows, os.kill SIGKILL
        on Linux/macOS. Idempotent."""
        if kp.proc.poll() is not None:
            return
        if os.name == "nt":
            self._taskkill_windows(kp.pid, force=True)
        else:
            import signal

            try:
                kp.proc.send_signal(signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        try:
            kp.proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                self._taskkill_windows(kp.pid, force=True, tree=True)
            kp.proc.wait(timeout=timeout_s)

    def kill_terminate(self, kp: KernelProcess, *, timeout_s: float = 5.0) -> None:
        """SIGTERM (graceful). The kernel worker does not implement a
        SIGTERM handler, so this effectively kills too on most platforms."""
        if kp.proc.poll() is not None:
            return
        if os.name == "nt":
            self._taskkill_windows(kp.pid, force=False)
        else:
            import signal

            try:
                kp.proc.send_signal(signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        try:
            kp.proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            self.kill_n9(kp, timeout_s=timeout_s)

    def restart(
        self,
        kp: KernelProcess,
        *,
        mode: str | None = None,
        config: dict | None = None,
        result_dir: Path | None = None,
        log_dir: Path | None = None,
    ) -> KernelProcess:
        """Spawn a fresh kernel subprocess. The old one is assumed dead
        (kill_n9 should have been called first)."""
        if kp.proc.poll() is None:
            self.kill_n9(kp)
        return self.start_kernel(
            kp.db_url,
            mode=mode or kp.mode,
            config=config or kp.config,
            result_dir=result_dir,
            log_dir=log_dir,
        )

    def verify_state(
        self,
        db_url: str,
        *,
        expected_run_id: str | None = None,
        include_goals: bool = True,
        include_plans: bool = False,
        include_evidence: bool = False,
        include_daemon_heartbeats: bool = False,
        result_dir: Path | None = None,
    ) -> dict:
        """Spawn a fresh kernel subprocess in verify_state mode and return
        the parsed JSON result."""
        config: dict[str, Any] = {
            "include_goals": include_goals,
            "include_plans": include_plans,
            "include_evidence": include_evidence,
            "include_daemon_heartbeats": include_daemon_heartbeats,
        }
        if expected_run_id is not None:
            config["run_id"] = expected_run_id

        kp = self.start_kernel(
            db_url, mode="verify_state", config=config, result_dir=result_dir
        )
        result = kp.read_result(timeout_s=10.0)
        if result is None:
            raise RuntimeError(
                f"verify_state worker did not write result; "
                f"returncode={kp.returncode}, log={kp.log_path}"
            )
        try:
            kp.proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            self.kill_n9(kp)
        return result

    # -- helpers ------------------------------------------------------------

    def _taskkill_windows(self, pid: int, *, force: bool, tree: bool = False) -> None:
        """Invoke taskkill. /F = force, /T = kill tree. WinError 128
        (process not found) is treated as success."""
        args = ["taskkill", "/PID", str(pid)]
        if force:
            args.append("/F")
        if tree:
            args.append("/T")
        try:
            subprocess.run(args, check=False, capture_output=True, timeout=5.0)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def wait_for_marker(
        self, kp: KernelProcess, *, timeout_s: float | None = None
    ) -> bool:
        """Block until the worker writes its crash-hook marker (or dies)."""
        timeout = timeout_s if timeout_s is not None else self.default_timeout_s
        deadline = time.time() + timeout
        marker = kp.marker_path
        if marker is None:
            return False
        while time.time() < deadline:
            if marker.exists():
                return True
            if kp.proc.poll() is not None:
                return False
            time.sleep(0.05)
        return False

    def wait_for_exit(self, kp: KernelProcess, *, timeout_s: float = 5.0) -> int:
        """Block until the worker exits; return its return code."""
        try:
            return kp.proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            self.kill_n9(kp)
            return -1

    def cleanup(self, kp: KernelProcess) -> None:
        """Best-effort: ensure subprocess is dead, remove result files."""
        if kp.proc.poll() is None:
            self.kill_n9(kp)
        for p in [kp.result_path, kp.marker_path]:
            if p is not None:
                try:
                    p.unlink()
                except (FileNotFoundError, PermissionError, OSError):
                    pass

    def kill_all(self) -> None:
        """Clean up any subprocesses still alive."""
        for kp in self._spawned:
            self.cleanup(kp)
        self._spawned.clear()


# ---------- asyncio bridge (optional) --------------------------------------


async def astart_kernel(inj: CrashInjector, *args, **kwargs) -> KernelProcess:
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: inj.start_kernel(*args, **kwargs)
    )


async def akill_n9(inj: CrashInjector, kp: KernelProcess) -> None:
    await asyncio.get_event_loop().run_in_executor(None, inj.kill_n9, kp)


__all__ = [
    "CrashInjector",
    "KernelProcess",
    "astart_kernel",
    "akill_n9",
]
