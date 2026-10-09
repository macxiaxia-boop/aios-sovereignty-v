"""commit_deep_audit_round2.py — Round 2 commits."""
import subprocess
from pathlib import Path

REPO = Path(r"D:\AIOS")

paths = [
    "AGENTS.md",
    "_agent-hub/AGENTS.md",
    "_agent-hub/scripts/deep_audit.py",
    "_agent-hub/memory/2026-10-09.md",
]

r = subprocess.run(["git", "add"] + paths, cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")

# commit parent
r = subprocess.run(
    ["git", "-C", str(REPO), "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "Round 2: AGENTS.md re-sync (CC added Phase H) + deep_audit.py fixes (await InMemoryRepository, shared repo for goal lookup, valid UUID)"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("commit:", r.stdout[-300:] if r.stdout else "", "|", r.stderr[-200:] if r.stderr else "")

r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"\nfinal dirty: {len(lines)}")