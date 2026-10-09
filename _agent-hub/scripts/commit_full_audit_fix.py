"""commit_full_audit_fix.py — 一次性 commit 全量查漏补缺的修复."""
import subprocess
from pathlib import Path

REPO = Path(r"D:\AIOS")

paths = [
    "AGENTS.md",
    "_agent-hub/AGENTS.md",
    "_agent-hub/v2/src/inbound_goal_generation.py",
    "_agent-hub/scripts/fix_inbound_active.py",
    "_agent-hub/scripts/fix_inbound_permission_scope_budget.py",
    "_agent-hub/scripts/verify_g002_active_v2.py",
    "_agent-hub/scripts/verify_inbound_end_to_end.py",
    "_agent-hub/scripts/audit_phase_g_real_usage.py",
    "_agent-hub/scripts/full_audit.py",
    "_agent-hub/scripts/populate_agent_knowledge_v6.py",
    "_agent-hub/scripts/populate_agent_knowledge_v5.py",
    "_agent-hub/scripts/populate_agent_knowledge_v4.py",
    "_agent-hub/scripts/populate_agent_knowledge_v3.py",
    "_agent-hub/scripts/populate_agent_knowledge_v2.py",
    "_agent-hub/scripts/populate_agent_knowledge.py",
    "_agent-hub/scripts/verify_g002_active.py",
    "_agent-hub/scripts/verify_g002_active_v2.py",
    "_agent-hub/memory/2026-10-09.md",
]

r = subprocess.run(["git", "add"] + paths, cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
print("git add:", r.stdout[-200:] if r.stdout else "", "|", r.stderr[-300:] if r.stderr else "")

r = subprocess.run(
    ["git", "-c", "user.name=Codex Supervisor", "-c", "user.email=codex@aios.local",
     "commit", "-m", "全量查漏补缺 Phase 1: 双 AGENTS.md 同步 + Phase B/C/D/E/F 段补全 + AGENTS.md Phase G 同段 + G002 inbound Active transition + decision audit + permission_scope.max_budget fix + 5 Agent knowledge 灌真实 failure clusters (merge_rate 71.43% > 70%) + 清 16 stale Pending goals"],
    cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("git commit:", r.stdout[-500:] if r.stdout else "", "|", r.stderr[-300:] if r.stderr else "")

r = subprocess.run(["git", "status", "--short"], cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(f"\nfinal dirty: {len(lines)}")
for l in lines[:10]:
    print(" ", l)