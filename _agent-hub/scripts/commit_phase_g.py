"""commit_phase_g.py — 一次性 commit Phase G 全部产物."""
import subprocess
from pathlib import Path

REPO = Path(r"D:\AIOS")

paths_to_add = [
    "_agent-hub/AGENTS.md",
    "_agent-hub/reports/aios_vnext_phase_g_done_20261009.md",
    "_agent-hub/memory/2026-10-09.md",
    "aios_tasks/aios_vnext/cards/G000_phase_g_acceptance_spec.md",
    "aios_tasks/aios_vnext/cards/G001_failure_feedback.md",
    "aios_tasks/aios_vnext/cards/G002_inbound_goal_generation.md",
    "aios_tasks/aios_vnext/cards/G003_cross_agent_knowledge.md",
    "aios_tasks/aios_vnext/cards/G004_verification_done.md",
    "aios_tasks/aios_vnext/INDEX.md",
    "aios_tasks/aios_vnext/scripts/run_failure_feedback.cmd",
    "_agent-hub/scripts/fix_test_fk_teardown.py",
    "_agent-hub/scripts/fix_v2_test_imports.py",
    "_agent-hub/scripts/fix_cli_aiosv2.py",
]

# 1. git add
r = subprocess.run(
    ["git", "add"] + paths_to_add,
    cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("git add stdout:", r.stdout[-300:] if r.stdout else "")
print("git add stderr:", r.stderr[-300:] if r.stderr else "")

# 2. git commit
r = subprocess.run(
    ["git", "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "Phase G (Learning Closure): FailureFeedback + inbound GoalContract generation + cross-agent knowledge"],
    cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("git commit stdout:", r.stdout[-500:] if r.stdout else "")
print("git commit stderr:", r.stderr[-300:] if r.stderr else "")

# 3. git log
r = subprocess.run(["git", "log", "--oneline", "-3"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
print("git log:", r.stdout)