"""commit_deep_audit_fix.py — Round 2 commit."""
import subprocess
from pathlib import Path

REPO = Path(r"D:\AIOS")

paths = [
    "AGENTS.md",
    "_agent-hub/AGENTS.md",
    "_agent-hub/scripts/deep_audit.py",
    "_agent-hub/scripts/fix_failure_feedback_uuid.py",
    "_agent-hub/scripts/fix_failure_feedback_uuid_v2.py",
    "_agent-hub/scripts/fix_test_failure_feedback_uuid.py",
    "_agent-hub/memory/2026-10-09.md",
]

r = subprocess.run(["git", "add"] + paths, cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
print("git add:", r.stderr[-300:] if r.stderr else "")

# kernel submodule
r = subprocess.run(["git", "-C", str(REPO / "kernel"), "add", "-A"], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("kernel git add:", r.stderr[-300:] if r.stderr else "")

# commit kernel
r = subprocess.run(
    ["git", "-C", str(REPO / "kernel"), "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "kernel: FailureFeedbackService UUID 容错 (G002-FIX-UUID) — production bug fix"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("kernel commit:", r.stdout[-300:] if r.stdout else "", "|", r.stderr[-200:] if r.stderr else "")

# commit parent
r = subprocess.run(
    ["git", "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "add", "-A"],
    cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace"
)
r = subprocess.run(
    ["git", "-C", str(REPO), "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "Round 2 全量查漏补缺: AGENTS.md 重新 sync + deep_audit.py 新工具 + UUID 容错 patch scripts"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("commit:", r.stdout[-300:] if r.stdout else "", "|", r.stderr[-200:] if r.stderr else "")

r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"\nfinal dirty: {len(lines)}")
for l in lines[:5]:
    print(" ", l)