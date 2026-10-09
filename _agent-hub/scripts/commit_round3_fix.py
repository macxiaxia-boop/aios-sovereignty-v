"""commit_round3_fix.py — Round 3 commits."""
import subprocess
from pathlib import Path

REPO = Path(r"D:\AIOS")

paths = [
    "_agent-hub/policy/strategy_gate.py",
    "_agent-hub/v2/tests/test_06_probes.py",
    "_agent-hub/scripts/fix_strategy_gate_prohibited_assets.py",
    "_agent-hub/scripts/fix_test_probe_claudecode.py",
    "_agent-hub/scripts/fix_probe_test_v3.py",
    "_agent-hub/scripts/commit_round3_fix.py",
    "_agent-hub/memory/2026-10-09.md",
]

r = subprocess.run(["git", "add"] + paths, cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
print("git add:", r.stderr[-300:] if r.stderr else "")

r = subprocess.run(
    ["git", "-C", str(REPO), "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "Round 3 全量查漏: StrategyGate._scan_for_prohibited_assets production bug fix (定义在 GateDecision 类外导致 AttributeError, 移到 StrategyGate 类内) + test_06_probes.py monkeypatch _resolve_claude_cli (Phase-2 装 MCP 后 probe live CLI 实际可达)"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("commit:", r.stdout[-300:] if r.stdout else "", "|", r.stderr[-200:] if r.stderr else "")

r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"\nfinal dirty: {len(lines)}")