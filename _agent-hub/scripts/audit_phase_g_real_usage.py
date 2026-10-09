"""audit_phase_g_real_usage.py — 全量查漏：检查 Phase G 实际运行状态."""
import os
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(r"D:\AIOS")
KERNEL = ROOT / "kernel"
V2 = ROOT / "_agent-hub" / "v2"

print("=" * 60)
print("Phase G 实际使用情况全量审计")
print("=" * 60)

# 1. GoalContract 是否真的生成
print("\n[1] G002 inbound_goal_generation 实际使用:")
gen_dir = V2 / "state" / "generated_goals"
if gen_dir.exists():
    files = sorted(gen_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    print(f"  generated_goals/ has {len(files)} files")
    if files:
        latest = files[0]
        print(f"  latest: {latest.name}")
        print(f"    mtime: {datetime.fromtimestamp(latest.stat().st_mtime).isoformat()}")
        try:
            d = json.loads(latest.read_text(encoding="utf-8"))
            print(f"    status: {d.get('status')}")
            print(f"    title: {d.get('title', '')[:60]}")
            print(f"    has 12 fields: {all(k in d for k in ['inferred_intent', 'preserve_capabilities', 'known_constraints', 'environment_context', 'success_criteria', 'failure_modes', 'permission_scope', 'missing_evidence', 'approved_tradeoffs', 'autonomous_scope', 'requires_authorization'])}")
        except Exception as e:
            print(f"    parse error: {e}")

# 2. GoalGuard 实际拦截
print("\n[2] F005 GoalGuard 实际拦截:")
risk_dir = V2 / "messages" / "risk"
if risk_dir.exists():
    files = sorted(risk_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    print(f"  risk/ has {len(files)} files")
    if files:
        latest = files[0]
        print(f"  latest: {latest.name}")
        print(f"    mtime: {datetime.fromtimestamp(latest.stat().st_mtime).isoformat()}")
        try:
            d = json.loads(latest.read_text(encoding="utf-8"))
            print(f"    type: {d.get('type')}")
            print(f"    verdict: {d.get('verdict')}")
            print(f"    failed_checks: {d.get('failed_checks', [])[:3]}")
        except Exception as e:
            print(f"    parse error: {e}")

# 3. FailureFeedback 是否真的反哺了 (看 Goal ORM 是否含 failure_modes 列)
print("\n[3] G001 FailureFeedback 反哺目标 (Goal ORM):")
try:
    import sys
    sys.path.insert(0, str(KERNEL / "src"))
    from aios_kernel.persistence.models import GoalORM
    cols = [c.name for c in GoalORM.__table__.columns]
    print(f"  GoalORM columns: {len(cols)}")
    has_fm = "failure_modes" in cols
    print(f"  has failure_modes col: {has_fm}")
    # 看 sample goal
    if has_fm:
        print(f"  failure_modes col type: {GoalORM.__table__.c.failure_modes.type}")
except Exception as e:
    print(f"  import error: {e}")

# 4. CrossAgentKnowledge 实际加载
print("\n[4] G003 CrossAgentKnowledge 实际:")
know_dir = r"D:\AIOS\_agent-hub\knowledge"
if os.path.exists(know_dir):
    files = list(Path(know_dir).glob("*_knowledge.json"))
    print(f"  knowledge/ has {len(files)} agent JSON files")
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            agent = d.get("agent", "?")
            fc_count = len(d.get("failure_clusters", []))
            cap_count = len(d.get("capability_index", []))
            print(f"  - {f.name}: agent={agent} failure_clusters={fc_count} capabilities={cap_count}")
        except Exception as e:
            print(f"  - {f.name}: parse error {e}")

# 5. v2 consumer service 实际状态
print("\n[5] v2 consumer 实际服务状态:")
import subprocess
r = subprocess.run(["sc", "query", "AIOSV2Consumer"], capture_output=True, text=True, encoding="utf-8", errors="replace")
state_line = ""
pid_line = ""
for line in r.stdout.splitlines():
    if "STATE" in line and "STATE" == line.strip().split(":")[0].strip():
        state_line = line
    if "PID" in line:
        pid_line = line
print(f"  {state_line}")
print(f"  {pid_line}")

# 6. DecisionAudit 是否真的记录
print("\n[6] F003 DecisionAudit 实际记录:")
try:
    from aios_kernel.domain.decision import DecisionAudit
    print(f"  DecisionAudit class: {DecisionAudit.__name__}")
    print(f"  SCHEMA_VERSION: {DecisionAudit.SCHEMA_VERSION}")
    print(f"  fields: {[f.name for f in DecisionAudit.__fields__.values()][:5]}...")
except Exception as e:
    print(f"  import error: {e}")

# 7. Inbound → GoalContract → GoalGuard 端到端 test
print("\n[7] 端到端 inbound → GoalContract → GoalGuard:")
try:
    from aios_kernel.intent.parser import IntentParser
    from aios_kernel.intent.llm_adapter import NullLLMAdapter
    from aios_kernel.governance.goal_guard import GoalGuard
    parser = IntentParser(llm_adapter=NullLLMAdapter())
    guard = GoalGuard()
    test_text = "30 分钟内完成 build, 宁可慢不要出错"
    parsed = parser.parse(test_text)
    print(f"  IntentParser.parse('{test_text}') returned: {type(parsed).__name__}")
    if hasattr(parsed, "title"):
        print(f"    parsed.title: {parsed.title}")
except Exception as e:
    print(f"  end-to-end test error: {e}")

# 8. SSOT 完整性
print("\n[8] AGENTS.md SSOT 阶段:")
agents_md = (ROOT / "_agent-hub" / "AGENTS.md").read_text(encoding="utf-8")
phases = ["Phase F", "Phase G", "Phase E", "Phase D", "Phase C", "Phase B", "Phase A"]
for p in phases:
    if p in agents_md:
        print(f"  ✓ {p} 段在 AGENTS.md")
    else:
        print(f"  ✗ {p} 段 MISSING")

# 9. AGENTS.md 在 D:\AIOS\ 也有一个 — 同步？
print("\n[9] 双 AGENTS.md 同步检查:")
top_agents = (ROOT / "AGENTS.md")
hub_agents = (ROOT / "_agent-hub" / "AGENTS.md")
if top_agents.exists() and hub_agents.exists():
    top_size = top_agents.stat().st_size
    hub_size = hub_agents.stat().st_size
    print(f"  D:\\AIOS\\AGENTS.md: {top_size} bytes")
    print(f"  D:\\AIOS\\_agent-hub\\AGENTS.md: {hub_size} bytes")
    import hashlib
    top_hash = hashlib.sha256(top_agents.read_bytes()).hexdigest()[:16]
    hub_hash = hashlib.sha256(hub_agents.read_bytes()).hexdigest()[:16]
    print(f"  top hash: {top_hash}")
    print(f"  hub hash: {hub_hash}")
    print(f"  identical: {top_hash == hub_hash}")

# 10. preflight 真跑
print("\n[10] preflight 真状态:")
r = subprocess.run(["python", r"D:\AIOS\aios_tasks\aios_vnext\preflight_check.py"],
                   cwd=r"D:\AIOS\aios_tasks\aios_vnext",
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
print(f"  exit code: {r.returncode}")
for line in r.stdout.splitlines():
    if "Status" in line or "Total Issues" in line or "CLEAN" in line or "DIRTY" in line:
        print(f"  {line}")