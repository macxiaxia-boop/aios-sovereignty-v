"""commit_remaining.py — commit 37 remaining + add NUL + quarantine to .gitignore."""
import subprocess
from pathlib import Path

REPO = Path(r"D:\AIOS")

# Update .gitignore: NUL + _quarantine/
gitignore = REPO / ".gitignore"
content = gitignore.read_text(encoding="utf-8")
adds = [
    "# Windows reserved name (cannot be added to git)",
    "NUL",
    "",
    "# Quarantined retired assets (Phase-3 deactivation)",
    "_quarantine/",
    "",
    "# Sovereignty-V ad-hoc investigation scripts (already in reports/)",
    "_agent-hub/reports/sovereignty-v/R*.py",
    "_agent-hub/reports/sovereignty-v/find_*.py",
]
new_section = "\n".join(adds)
if "NUL\n" not in content:
    content = content.rstrip() + "\n" + new_section + "\n"
    gitignore.write_text(content, encoding="utf-8")
    print(".gitignore updated: +NUL +_quarantine/ +sovereignty-v/R*.py")

# git add
r = subprocess.run(["git", "add", "-A"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
print("git add:", r.stderr[-300:] if r.stderr else "")

# commit
r = subprocess.run(
    ["git", "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "全量查漏补缺 Phase 3: 清 stale generated_goals (16 Pending) + 清 stale install_aios_loop/aios_watchdog.cmd (已 retire) + .gitignore: NUL reserved + _quarantine/ + sovereignty-v/R*.py"],
    cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("git commit:", r.stdout[-300:] if r.stdout else "", "|", r.stderr[-300:] if r.stderr else "")

r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"\nfinal dirty: {len(lines)}")
for l in lines[:15]:
    print(" ", l)