"""commit_round3_final.py — Round 3 final commits."""
import subprocess
from pathlib import Path

REPO = Path(r"D:\AIOS")

paths = [
    "_agent-hub/policy/strategy_gate.py",
    "_agent-hub/v2/tests/test_06_probes.py",
    "_agent-hub/scripts/fix_strategy_gate_prohibited_assets.py",
    "_agent-hub/scripts/fix_test_probe_claudecode.py",
    "_agent-hub/scripts/fix_probe_test_v3.py",
    "_agent-hub/scripts/fix_strategy_gate_fingerprint.py",
    "_agent-hub/scripts/fix_aios_v2_bridge.py",
    "_agent-hub/scripts/check_pa_match_v4.py",
    "_agent-hub/scripts/check_strategy_gate_debug.py",
    "_agent-hub/scripts/clear_pycaches.py",
    "_agent-hub/scripts/commit_round3_final.py",
    "_agent-hub/memory/2026-10-09.md",
]

r = subprocess.run(["git", "add"] + paths, cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
print("git add:", r.stderr[-300:] if r.stderr else "")

r = subprocess.run(
    ["git", "-C", str(REPO), "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "Round 3 final: StrategyGate._scan_for_prohibited_assets 移到类内 (生产 bug) + fingerprint logic 收紧 (len>=6, >=2 hits, boundary check) 防止 'loop' false-match 'loopback' + _aios_v2_envelope_bridge.py src.queue -> src.message_queue (R286 MCP bridge) + test_06_probes.py monkeypatch _resolve_claude_cli (Phase-2 装 MCP 后)"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("commit:", r.stdout[-300:] if r.stdout else "", "|", r.stderr[-200:] if r.stderr else "")

r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"\nfinal dirty: {len(lines)}")