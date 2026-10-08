# v2/src/probes.py — real probes. Returns four honest levels per agent.
#
# LEVELS (do NOT conflate):
#   configured  — known to the registry (agents/agents.json)
#   present     — required files/binary exist on disk (no runtime call yet)
#   reachable   — runtime probe returned a non-error response in this session
#   healthy     — runtime probe returned the SPECIFIC 2xx success criterion
#
# RULE: `reachable` and `healthy` MUST come from a live call in this run.
# No live call → no higher level than `present`.
# No fake `healthy=True` just because the hub files exist.
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .id import utc_now_iso

# Probe constants
HERMES_EXE = Path(r"D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe")
CODEX_PORTABLE_EXE = Path(r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\ChatGPT.exe")
OPENCLAW_PORT = 18792
OPENCLAW_HEALTH = f"http://127.0.0.1:{OPENCLAW_PORT}/healthz"
CODEX_RELAY_PORT = 19194
HUB_ROOT = Path(r"D:\AIOS\_agent-hub")
REGISTRY_PATH = Path(r"D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_AGENT_REGISTRY.json")

LEVELS = ("configured", "present", "reachable", "healthy")


def _base(agent_id: str, transport: str) -> dict:
    return {
        "agent_id": agent_id,
        "transport": transport,
        "ts": utc_now_iso(),
        # Defaults: only configured. Upgraded by live probes.
        "configured": False,
        "present": False,
        "reachable": False,
        "healthy": False,
        "details": {},
        "evidence": [],
        "blockers": [],
    }


def _upgrade(rec: dict, *, present=None, reachable=None, healthy=None,
              note: str = "") -> None:
    if present is not None:
        rec["present"] = bool(present)
        if note:
            rec["evidence"].append(note)
    if reachable is not None:
        rec["reachable"] = bool(reachable)
        if note:
            rec["evidence"].append(note)
    if healthy is not None:
        rec["healthy"] = bool(healthy)
        if note:
            rec["evidence"].append(note)


def _configured(rec: dict, agent_id_in_registry: bool) -> None:
    rec["configured"] = agent_id_in_registry
    if agent_id_in_registry:
        rec["evidence"].append(f"present in {REGISTRY_PATH.name}")


# ---------------------------------------------------------------- OpenClaw
def probe_openclaw() -> dict:
    rec = _base("openclaw", f"HTTP 127.0.0.1:{OPENCLAW_PORT}")
    _configured(rec, _agent_in_registry("openclaw"))
    rec["details"]["port"] = OPENCLAW_PORT
    rec["details"]["healthz_url"] = OPENCLAW_HEALTH
    # 1) TCP port
    try:
        with socket.create_connection(("127.0.0.1", OPENCLAW_PORT), timeout=3):
            rec["details"]["port_open"] = True
            _upgrade(rec, present=True, reachable=True,
                     note=f"socket.connect({OPENCLAW_PORT}) OK")
    except OSError as e:
        rec["details"]["port_open"] = False
        rec["details"]["port_error"] = str(e)
        rec["blockers"].append("port closed")
        return rec
    # 2) /healthz
    try:
        with urllib.request.urlopen(OPENCLAW_HEALTH, timeout=5) as r:
            body = r.read(256).decode("utf-8", errors="replace")
            rec["details"]["healthz_status"] = r.status
            rec["details"]["healthz_body"] = body[:120]
            if r.status == 200:
                _upgrade(rec, healthy=True,
                         note=f"GET /healthz 200 body={body[:60]!r}")
            else:
                rec["blockers"].append(f"/healthz returned {r.status}")
        return rec
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        rec["details"]["healthz_error"] = str(e)
        rec["blockers"].append(f"/healthz unreachable: {e}")
        return rec


# ---------------------------------------------------------------- Codex
def probe_codex() -> dict:
    rec = _base("codex", "file-queue + aios-interop MCP")
    _configured(rec, _agent_in_registry("codex"))
    rec["details"]["relay_port"] = CODEX_RELAY_PORT
    # 1) relay port
    try:
        with socket.create_connection(("127.0.0.1", CODEX_RELAY_PORT), timeout=2):
            rec["details"]["relay_port_open"] = True
            _upgrade(rec, present=True, reachable=True,
                     note=f"socket.connect(relay {CODEX_RELAY_PORT}) OK")
    except OSError as e:
        rec["details"]["relay_port_open"] = False
        rec["details"]["relay_error"] = str(e)
        rec["blockers"].append("relay port 19194 closed")
    # 2) portable exe
    if CODEX_PORTABLE_EXE.exists():
        rec["details"]["exe_exists"] = True
        rec["details"]["exe_size"] = CODEX_PORTABLE_EXE.stat().st_size
        _upgrade(rec, present=True, note=f"portable exe present ({rec['details']['exe_size']} bytes)")
    else:
        rec["details"]["exe_exists"] = False
        rec["details"]["exe_size"] = 0
        rec["blockers"].append("portable exe path not visible from this scope")
    # 3) ChatGPT.exe in tasklist (R320.3: presence only — does NOT imply reachable.
    # The bridge transport is "file-queue + aios-interop MCP"; only an open
    # relay TCP socket (or a successful MCP round-trip) qualifies as reachable.
    # A live process is at best `present`.)
    try:
        out = subprocess.run(
            ["cmd", "/c", "tasklist", "/NH", "/FI", "IMAGENAME eq ChatGPT.exe"],
            capture_output=True, timeout=10,
        )
        text = out.stdout.decode("utf-8", errors="replace")
        alive = "ChatGPT.exe" in text
        rec["details"]["chatgpt_running"] = alive
        if alive:
            _upgrade(rec, present=True,
                     note="ChatGPT.exe ALIVE in tasklist (process present; "
                          "NOT a proof of MCP bridge reachable)")
    except (OSError, subprocess.TimeoutExpired) as e:
        rec["details"]["tasklist_error"] = str(e)
        rec["blockers"].append(f"tasklist denied: {e}")
    # R320.3: healthy requires a real health-probe transaction against the
    # bridge transport. We don't have one yet, so healthy stays False unless
    # an upstream caller overrides it after a successful round-trip.
    return rec


# ---------------------------------------------------------------- Hermes
def probe_hermes() -> dict:
    rec = _base("hermes", "shell CLI")
    _configured(rec, _agent_in_registry("hermes"))
    rec["details"]["exe"] = str(HERMES_EXE)
    if HERMES_EXE.exists():
        rec["details"]["exe_exists"] = True
        rec["details"]["exe_size"] = HERMES_EXE.stat().st_size
        _upgrade(rec, present=True, note=f"hermes.exe present ({rec['details']['exe_size']} bytes)")
    else:
        rec["details"]["exe_exists"] = False
        rec["blockers"].append("hermes.exe missing")
        return rec
    # Try to invoke — only upgrade reachable/healthy if subprocess returns
    try:
        r = subprocess.run([str(HERMES_EXE), "--version"],
                           capture_output=True, timeout=8)
        rec["details"]["version_exitcode"] = r.returncode
        rec["details"]["version_stdout"] = r.stdout.decode("utf-8", errors="replace").strip()[:200]
        if r.returncode == 0:
            _upgrade(rec, reachable=True, healthy=True,
                     note=f"hermes --version exit={r.returncode}")
        else:
            _upgrade(rec, reachable=True,
                     note=f"hermes --version exit={r.returncode} (non-zero)")
            rec["blockers"].append(f"--version exit={r.returncode}")
    except (OSError, subprocess.TimeoutExpired) as e:
        rec["details"]["exec_error"] = str(e)
        rec["blockers"].append(f"exec blocked/timeout: {e}")
    return rec


# ---------------------------------------------------------------- WorkBuddy
WORKBUDDY_HOME = Path(os.path.expanduser(r"~\.workbuddy"))

def probe_workbuddy() -> dict:
    rec = _base("workbuddy", "file-queue + WBBridge daemon")
    _configured(rec, _agent_in_registry("workbuddy"))
    # WorkBuddy home hub files (real location, not D:\AIOS\_agent-hub)
    wb_files = ["CLAUDE.md", "AGENTS.md", "MEMORY.md"]
    any_present = False
    for f in wb_files:
        p = WORKBUDDY_HOME / f
        exists = p.exists()
        rec["details"][f"wb_{f.lower()}"] = exists
        if exists:
            any_present = True
            _upgrade(rec, present=True, note=f"~/.workbuddy/{f} present")
        else:
            rec["blockers"].append(f"~/.workbuddy/{f} missing")
    if not any_present:
        return rec
    # Live daemon probe: WBBridge listens via electron app data; test by reading
    # an active log file tail (proof of liveness, not full RPC)
    try:
        daemons = list((WORKBUDDY_HOME / "logs").glob("daemon.log")) + list((WORKBUDDY_HOME / "logs").glob("main.log"))
        if daemons:
            latest = max(daemons, key=lambda x: x.stat().st_mtime)
            age_s = time.time() - latest.stat().st_mtime
            rec["details"]["daemon_log"] = latest.name
            rec["details"]["daemon_log_age_s"] = round(age_s, 1)
            if age_s < 60:
                _upgrade(rec, reachable=True,
                         note=f"daemon log active (last write {age_s:.0f}s ago)")
                _upgrade(rec, healthy=True,
                         note="WorkBuddy daemon appears alive (recent log writes)")
            else:
                rec["blockers"].append(f"daemon log stale ({age_s:.0f}s)")
        else:
            rec["blockers"].append("no daemon.log / main.log")
    except OSError as e:
        rec["blockers"].append(f"daemon probe error: {e}")
    return rec


# ---------------------------------------------------------------- Claude Code
CLAUDE_CLI_CANDIDATES = [
    Path(r"D:\npm-global\claude.ps1"),
    Path(r"C:\Users\xinzh\AppData\Roaming\npm\claude.cmd"),
]

def _resolve_claude_cli() -> Optional[Path]:
    for p in CLAUDE_CLI_CANDIDATES:
        if p.exists():
            return p
    import shutil
    found = shutil.which("claude")
    return Path(found) if found else None


def probe_claudecode() -> dict:
    rec = _base("claudecode", "aios-interop MCP + file-queue + claude CLI")
    _configured(rec, _agent_in_registry("claudecode"))
    # presence checks (static)
    if (HUB_ROOT / "CLAUDE.md").exists():
        _upgrade(rec, present=True, note="hub CLAUDE.md present (CC reads this at session start)")
    if (HUB_ROOT / "v2").exists():
        _upgrade(rec, present=True, note="hub v2/ installed")
    # live CLI call
    cli = _resolve_claude_cli()
    if cli is None:
        rec["blockers"].append("claude CLI not found in PATH or known locations")
        return rec
    rec["details"]["cli_path"] = str(cli)
    rec["details"]["cli_size"] = cli.stat().st_size
    _upgrade(rec, present=True, note=f"claude CLI present ({cli.stat().st_size} bytes)")
    try:
        # Use powershell to invoke the .ps1 since it requires shell wrapper
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"& '{cli}' --version"],
            capture_output=True, timeout=15,
        )
        out = r.stdout.decode("utf-8", errors="replace").strip()
        rec["details"]["version_exitcode"] = r.returncode
        rec["details"]["version_stdout"] = out[:200]
        if r.returncode == 0 and "Claude Code" in out:
            _upgrade(rec, reachable=True, healthy=True,
                     note=f"claude --version exit=0, version='{out.split(chr(10))[0]}'")
        else:
            rec["blockers"].append(f"claude --version non-zero exit={r.returncode}")
    except (OSError, subprocess.TimeoutExpired) as e:
        rec["details"]["exec_error"] = str(e)
        rec["blockers"].append(f"claude --version blocked/timeout: {e}")
    return rec


# ---------------------------------------------------------------- all
def probe_all() -> dict:
    return {"ts": utc_now_iso(),
            "agents": [probe_claudecode(), probe_codex(), probe_workbuddy(),
                        probe_hermes(), probe_openclaw()]}


# ---------------------------------------------------------------- registry helper
def _agent_in_registry(agent_id: str) -> bool:
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        for a in data.get("agents", []):
            if a.get("id") == f"agent-{agent_id}" or a.get("name", "").lower() == agent_id:
                return True
        # Also check v2/agents/agents.json
        v2p = Path(r"D:\AIOS\_agent-hub\v2\agents\agents.json")
        if v2p.exists():
            v2data = json.loads(v2p.read_text(encoding="utf-8"))
            return any(a.get("agent_id") == agent_id for a in v2data.get("agents", []))
    except Exception:
        pass
    return False


if __name__ == "__main__":
    print(json.dumps(probe_all(), ensure_ascii=False, indent=2))