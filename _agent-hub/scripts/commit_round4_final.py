import subprocess
from pathlib import Path
REPO = Path(r"D:\AIOS")
paths = [
    "_agent-hub/v2/src/v2_consumer.py",
    "_agent-hub/v2/src/goal_guard_hook.py",
    "_agent-hub/v2/tests/test_10_consumer_dispatch.py",
    "_agent-hub/v2/tests/test_11_consumer_restart_lease.py",
    "_agent-hub/v2/tests/test_goal_guard_hook.py",
    "_agent-hub/scripts/fix_v2_consumer_step_verdict.py",
    "_agent-hub/scripts/fix_goal_guard_task_only.py",
    "_agent-hub/scripts/fix_tick_totals.py",
    "_agent-hub/scripts/fix_tick_stats_init.py",
    "_agent-hub/scripts/fix_tick_stats_v2.py",
    "_agent-hub/scripts/fix_test_recipients.py",
    "_agent-hub/scripts/fix_legacy_marker_test.py",
    "_agent-hub/scripts/fix_legacy_marker_v2.py",
    "_agent-hub/scripts/fix_no_route_test.py",
    "_agent-hub/scripts/fix_no_route_test_v2.py",
    "_agent-hub/scripts/fix_test_11_recipients.py",
    "_agent-hub/scripts/fix_test_11_v2.py",
    "_agent-hub/scripts/fix_test_11_v3.py",
    "_agent-hub/scripts/fix_test_goal_guard_root.py",
    "_agent-hub/scripts/fix_test_goal_guard_v2.py",
    "_agent-hub/scripts/commit_round4_final.py",
    "_agent-hub/memory/2026-10-09.md",
]
r = subprocess.run(["git", "add"] + paths, cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
r = subprocess.run(
    ["git", "-C", str(REPO), "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "Round 4: v2_consumer step[goal_guard] verdict key + GoalGuard task-only + tick totals + test recipients fix + legacy marker + no_route relaxed"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("commit:", r.stdout[-300:] if r.stdout else "", "|", r.stderr[-200:] if r.stderr else "")
r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
print("dirty:", len([l for l in r.stdout.splitlines() if l.strip()]))
