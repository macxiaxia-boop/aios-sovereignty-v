"""commit_all_dirty.py — 一次性 commit 所有 dirty (用户要求"全部做掉")。

策略:
1. 把 _backups_relinked, node_modules, .venv 加入 .gitignore (这些是 pre-existing 系统噪音, 不应入仓)
2. git add -A 把其他全部 add (modified + untracked)
3. git commit
"""
import subprocess
from pathlib import Path

REPO = Path(r"D:\AIOS")

# 1. 更新 .gitignore (把 _backups_relinked, node_modules, .venv 加进去)
gitignore = REPO / ".gitignore"
content = gitignore.read_text(encoding="utf-8")
adds = [
    "",
    "# Pre-existing long-path backups (cannot enter git; blocked by OS path limit)",
    "_backups_relinked_*/",
    "",
    "# Node modules + python venv (should never be tracked)",
    "**/node_modules/",
    "**/__pycache__/",
    "**/.venv/",
    "**/venv/",
]
new_section = "\n".join(adds)
if "_backups_relinked_*/" not in content:
    content = content.rstrip() + "\n" + new_section + "\n"
    gitignore.write_text(content, encoding="utf-8")
    print(".gitignore updated: +_backups_relinked_*, +node_modules, +__pycache__, +.venv")

# 2. git add -A (with new .gitignore, _backups_relinked 等被排除)
r = subprocess.run(["git", "add", "-A"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("git add -A stdout:", r.stdout[:200] if r.stdout else "")
print("git add -A stderr:", r.stderr[:200] if r.stderr else "")

# 3. 看 remaining dirty
r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"after git add -A: {len(lines)} dirty")
if lines:
    print("first 10:", lines[:10])

# 4. commit
r = subprocess.run(
    ["git", "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "Track Phase-2/3 policy + reports + knowledge + helper scripts + state updates + gitignore long-path blocks"],
    cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("git commit stdout:", r.stdout[-500:] if r.stdout else "")
print("git commit stderr:", r.stderr[-300:] if r.stderr else "")

# 5. 看 final dirty
r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"\nfinal dirty: {len(lines)}")
for l in lines[:30]:
    print(" ", l)