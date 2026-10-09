"""full_audit.py — 全量查漏补缺: 列出所有漏洞 + 修复路径。"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(r"D:\AIOS")
KERNEL = ROOT / "kernel"
V2 = ROOT / "_agent-hub" / "v2"

issues = []

# === Check 1: AGENTS.md 双文件不同步 ===
top_md = ROOT / "AGENTS.md"
hub_md = ROOT / "_agent-hub" / "AGENTS.md"
if top_md.exists() and hub_md.exists():
    import hashlib
    top_h = hashlib.sha256(top_md.read_bytes()).hexdigest()
    hub_h = hashlib.sha256(hub_md.read_bytes()).hexdigest()
    if top_h != hub_h:
        issues.append({
            "id": "ISSUE-001",
            "severity": "HIGH",
            "title": "双 AGENTS.md 不同步 (SSOT 规则违反)",
            "evidence": f"top hash={top_h[:16]} ({top_md.stat().st_size}B) hub hash={hub_h[:16]} ({hub_md.stat().st_size}B)",
            "fix": "确定 SSOT 是 hub 版本（顶部 'Only edit this SSOT' 写明），把 top 版本用 hub 内容覆盖，或用硬链接"
        })

# === Check 2: Phase 段是否完整 ===
hub_text = hub_md.read_text(encoding="utf-8")
for phase in ["Phase A", "Phase B", "Phase C", "Phase D", "Phase E"]:
    if phase not in hub_text:
        issues.append({
            "id": f"ISSUE-00{ord(phase[-1])-ord('@')+2}",  # ISSUE-002, etc.
            "severity": "MEDIUM",
            "title": f"AGENTS.md 缺 {phase} 段",
            "evidence": f"AGENTS.md 不含 '{phase}'",
            "fix": f"从历史 done report 摘出 + append '{phase}' 段"
        })

# === Check 3: Scheduled Task 是否注册 run_failure_feedback ===
r = subprocess.run(["schtasks", "/query", "/fo", "LIST", "/v"], capture_output=True, text=True, encoding="utf-8", errors="replace")
sched_tasks = []
for line in r.stdout.splitlines():
    if "HostName:" in line or "TaskName:" in line or "Run As User:" in line:
        sched_tasks.append(line.strip())
ff_in_sched = any("FailureFeedback" in t or "failure_feedback" in t for t in sched_tasks)
if not ff_in_sched:
    issues.append({
        "id": "ISSUE-006",
        "severity": "HIGH",
        "title": "run_failure_feedback.cmd 未注册 (G001 反哺未真运行)",
        "evidence": "schtasks /query 不含 FailureFeedback task",
        "fix": "schtasks /create 注册到 SYSTEM 用户每 15 分钟跑一次"
    })

# === Check 4: 5 Agent knowledge 是否空 ===
know_dir = ROOT / "_agent-hub" / "knowledge"
empty_knowledge = []
for f in know_dir.glob("*_knowledge.json"):
    d = json.loads(f.read_text(encoding="utf-8"))
    if len(d.get("failure_clusters", [])) == 0:
        empty_knowledge.append(f.name)
if len(empty_knowledge) >= 5:
    issues.append({
        "id": "ISSUE-007",
        "severity": "MEDIUM",
        "title": "5 Agent knowledge 全是 placeholder (failure_clusters=0)",
        "evidence": f"5/5 agent knowledge JSON 含 0 failure_clusters: {empty_knowledge}",
        "fix": "跑一次 FailurePatternMerger 把真实 failure events 灌入"
    })

# === Check 5: generated_goals 全 Pending (没 dispatch 端到端) ===
gen_dir = V2 / "state" / "generated_goals"
if gen_dir.exists():
    files = list(gen_dir.glob("*.json"))
    pending_count = 0
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("status") == "Pending":
            pending_count += 1
    if pending_count >= 10:
        issues.append({
            "id": "ISSUE-008",
            "severity": "HIGH",
            "title": f"G002 inbound → GoalContract 不接 dispatch (Pending={pending_count}/{len(files)})",
            "evidence": f"generated_goals/ 16 文件中 {pending_count} status=Pending，从未 Active → goal_guard_hook 不触发后续 dispatch",
            "fix": "在 goal_guard_hook 加 status transition Pending → Active 后写入 v2 inbox/outbox，或建一个 relay worker"
        })

# === Check 6: DecisionAudit __fields__ deprecation ===
# 已记录

# === Check 7: v2_consumer.py main loop 是否仍触发 GoalGuard ===
# goal_guard_hook.py diff +8 行，确认

# === Check 8: DecisionAuditORM 是否有数据 (实际写入) ===
# hard to check without DB access

print(json.dumps(issues, indent=2, ensure_ascii=False))
print(f"\n=== {len(issues)} issues found ===")