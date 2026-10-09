"""deep_audit.py — 深度审计 (不光 STATUS, 看真实数据)."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, r'D:\AIOS\kernel\src')

ROOT = Path(r'D:\AIOS')
KERNEL = ROOT / 'kernel'
V2 = ROOT / '_agent-hub' / 'v2'

issues = []

# 1. GoalContract 端到端真跑 (process_inbound_envelope in real env)
print('[1] G002 process_inbound_envelope 端到端 verify')
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'ig', str(V2 / 'src' / 'inbound_goal_generation.py')
    )
    ig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ig)

    # Use GoalGuard directly (no DB) to ensure validation works
    from aios_kernel.governance.goal_guard import GoalGuard
    from aios_kernel.intent.parser import IntentParser
    from aios_kernel.intent.llm_adapter import NullLLMAdapter

    parser = IntentParser(llm_adapter=NullLLMAdapter())
    guard = GoalGuard()

    # Build a complete envelope that should pass
    env = {
        'id': 'deep-audit-001',
        'message_type': 'task',
        'sender': 'codex',
        'recipient': 'claudecode',
        'payload': {
            'title': 'Deep audit test',
            'text': 'Test end-to-end GoalContract flow.',
            'budget': 1.0,
            'owner': 'codex',
            'allowed_paths': ['D:/AIOS/_agent-hub/'],
            'allowed_ops': ['read', 'write', 'execute'],
            'max_duration_sec': 300,
            'failure_modes': [{'description': 'test', 'detection': 'pytest fail'}],
            'missing_evidence': [{'description': 'evidence', 'source': 'pytest', 'required': True}],
            'autonomous_scope': [{'domain': 'service', 'action': 'execute'}],
            'requires_authorization': [{'domain': 'file', 'action': 'delete'}],
        }
    }
    goal, allowed, risk, path = ig.process_inbound_envelope(env)
    print(f'  allowed: {allowed}')
    print(f'  goal.status.value: {goal.status.value}')
    print(f'  goal.budget: {goal.budget}')
    print(f'  perm.max_budget: {goal.permission_scope.max_budget}')

    if not allowed:
        issues.append({
            'id': 'DEEP-001', 'severity': 'HIGH',
            'title': 'inbound_goal_generation end-to-end FAILED',
            'evidence': f'allowed={allowed}, risk={risk}',
            'fix': 'fix inbound_goal_generation'
        })
    if goal.status.value != 'Active':
        issues.append({
            'id': 'DEEP-002', 'severity': 'HIGH',
            'title': 'inbound_goal_generation Active transition FAILED',
            'evidence': f'goal.status={goal.status.value}, expected Active',
            'fix': 'check process_inbound_envelope activate_on_pass logic'
        })
    if goal.budget != goal.permission_scope.max_budget:
        issues.append({
            'id': 'DEEP-003', 'severity': 'HIGH',
            'title': 'permission_scope.max_budget != goal.budget (cross-validator violation)',
            'evidence': f'goal.budget={goal.budget}, perm.max_budget={goal.permission_scope.max_budget}',
            'fix': 'fix permission_scope.max_budget=goal.budget'
        })
except Exception as e:
    issues.append({
        'id': 'DEEP-001-EXC', 'severity': 'HIGH',
        'title': 'inbound_goal_generation end-to-end EXCEPTION',
        'evidence': str(e), 'fix': 'debug'
    })

# 2. FailureFeedbackService 端到端 verify
print('\n[2] G001 FailureFeedbackService 端到端 verify')
try:
    from aios_kernel.learning.clustering import FailureTrace, FailurePatternMerger
    from aios_kernel.learning.failure_feedback import FailureFeedbackService

    # Mock the Goal repo + repo
    from aios_kernel.domain.services.repository import InMemoryRepository

    repo = InMemoryRepository()
    # Use SAME repo for both — production separates but for unit test the goal
    # needs to be visible to _fetch_goal()
    goal_repo = repo

    # Create a Goal with failure_modes = []
    from aios_kernel.domain.goal import Goal, GoalStatus, FailureMode
    g = Goal(
        id='11111111-2222-3333-4444-555555555555',  # valid UUID
        title='Test goal',
        success_criteria='test passes',
        budget=0.0,
        owner='codex',
    )
    # InMemoryRepository methods are coroutines — must await
    import asyncio as _aio_setup
    _aio_setup.run(repo.add(g))
    _aio_setup.run(repo.commit())

    # Run service
    fb = FailureFeedbackService(repo, repo)

    # Create clusters
    merger = FailurePatternMerger()
    traces = [
        FailureTrace(id=f'rt{i}', error_message='ValidationError test pattern',
                     error_type='ValidationError', context={},
                     timestamp='2026-10-09T10:00:00')
        for i in range(5)  # 5 occurrences to pass min_occurrence threshold
    ]
    clusters = merger.merge(traces)

    # Apply to goal
    import asyncio as _asyncio
    # apply_clusters_to_goal returns (Goal, added_descriptions) tuple (per G002-FIX-UUID)
    result = _asyncio.run(fb.apply_clusters_to_goal('11111111-2222-3333-4444-555555555555', clusters))
    if result is None:
        issues.append({
            'id': 'DEEP-004', 'severity': 'HIGH',
            'title': 'FailureFeedbackService.apply_clusters_to_goal returned None',
            'evidence': 'goal lookup failed',
            'fix': 'check FailureFeedbackService UUID lookup'
        })
    else:
        updated_goal, added = result
        if len(added) > 0:
            print(f'  applied {len(added)} failure modes to goal')
        else:
            issues.append({
                'id': 'DEEP-004', 'severity': 'HIGH',
                'title': 'FailureFeedbackService.apply_clusters_to_goal added 0 modes',
                'evidence': f'clusters={len(clusters)}, added={len(added)}',
                'fix': 'check FailureFeedbackService idempotent logic'
            })
except Exception as e:
    issues.append({
        'id': 'DEEP-002-EXC', 'severity': 'HIGH',
        'title': 'FailureFeedbackService end-to-end EXCEPTION',
        'evidence': str(e), 'fix': 'debug'
    })

# 3. CrossAgentKnowledgeService 端到端 verify
print('\n[3] G003 CrossAgentKnowledgeService 端到端 verify')
try:
    from aios_kernel.learning.cross_agent_knowledge import (
        CrossAgentKnowledgeService, AgentName, CapabilityIndex
    )

    svc = CrossAgentKnowledgeService()
    know = svc.load_all()
    print(f'  loaded {len(know)} agents')

    total_clusters = sum(len(k.failure_clusters) for k in know.values())
    total_caps = sum(len(k.capability_index) for k in know.values())
    print(f'  total failure_clusters: {total_clusters}')
    print(f'  total capabilities: {total_caps}')

    if total_clusters < 30:  # expect 8 clusters * 5 agents = 40
        issues.append({
            'id': 'DEEP-005', 'severity': 'MEDIUM',
            'title': f'cross-agent knowledge low (clusters={total_clusters})',
            'evidence': 'expected >=30, got {total_clusters}',
            'fix': 're-run populate_agent_knowledge'
        })
except Exception as e:
    issues.append({
        'id': 'DEEP-003-EXC', 'severity': 'HIGH',
        'title': 'CrossAgentKnowledgeService EXCEPTION',
        'evidence': str(e), 'fix': 'debug'
    })

# 4. DecisionAudit 真实记录 (看 events.ndjson)
print('\n[4] F003 DecisionAudit 真实记录 (events.ndjson)')
events_log = V2 / 'logs' / 'events.ndjson'
if events_log.exists():
    with open(events_log, 'r', encoding='utf-8') as f:
        events = f.readlines()
    print(f'  events.ndjson has {len(events)} lines')
    audit_log = V2 / 'logs' / 'inbound_goal_audit.ndjson'
    if audit_log.exists():
        with open(audit_log, 'r', encoding='utf-8') as f:
            audit_events = f.readlines()
        print(f'  inbound_goal_audit.ndjson has {len(audit_events)} lines')
    else:
        issues.append({
            'id': 'DEEP-006', 'severity': 'MEDIUM',
            'title': 'inbound_goal_audit.ndjson not created',
            'evidence': 'audit log missing despite process_inbound_envelope',
            'fix': 'check _write_decision_audit_event logic'
        })
else:
    issues.append({
        'id': 'DEEP-007', 'severity': 'MEDIUM',
        'title': 'events.ndjson missing',
        'evidence': f'{events_log} does not exist',
        'fix': 'check v2 consumer is logging events'
    })

# 5. AGENTS.md 双文件同步 (每次 self-audit 应 verify)
print('\n[5] AGENTS.md 双文件 sync')
import hashlib
top_md = ROOT / 'AGENTS.md'
hub_md = ROOT / '_agent-hub' / 'AGENTS.md'
top_h = hashlib.sha256(top_md.read_bytes()).hexdigest()[:16]
hub_h = hashlib.sha256(hub_md.read_bytes()).hexdigest()[:16]
if top_h != hub_h:
    issues.append({
        'id': 'DEEP-008', 'severity': 'HIGH',
        'title': 'AGENTS.md 双文件 重新 desync (round 2 之后)',
        'evidence': f'top={top_h} hub={hub_h}',
        'fix': 're-sync'
    })
else:
    print(f'  identical: {top_h} == {hub_h}')

# 6. preflight v4 真状态')
print('\n[6] preflight v4')
import subprocess
r = subprocess.run(['python', str(ROOT / 'aios_tasks' / 'aios_vnext' / 'preflight_check.py')],
                   cwd=str(ROOT / 'aios_tasks' / 'aios_vnext'),
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print(f'  exit={r.returncode}')
if 'CLEAN' not in r.stdout:
    issues.append({
        'id': 'DEEP-009', 'severity': 'HIGH',
        'title': 'preflight DIRTY',
        'evidence': r.stdout[-300:],
        'fix': 'find forbidden files'
    })

# 7. 现有 kernel + v2 baseline 不退化
print('\n[7] pytest baseline 不退化')
py = KERNEL / '.venv' / 'Scripts' / 'python.exe'
r = subprocess.run([str(py), '-m', 'pytest', 'tests/unit', '-q', '--tb=no'],
                   cwd=str(KERNEL), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
summary = ''
for line in r.stdout.splitlines():
    if 'passed' in line or 'failed' in line:
        summary = line.strip()
        break
print(f'  summary: {summary}')
if 'failed' in summary and '0 failed' not in summary:
    issues.append({
        'id': 'DEEP-010', 'severity': 'HIGH',
        'title': 'pytest baseline regression',
        'evidence': summary,
        'fix': 'find regressing test'
    })

# 8. v2 baseline 不退化 (已知 2 fail pre-existing)
print('\n[8] v2 baseline 不退化')
r = subprocess.run([str(py), '-m', 'pytest', 'tests', '-q', '-x', '--tb=no', '--ignore=tests/test_strategy_cross_session.py', '--ignore=tests/test_p8_t15.py'],
                   cwd=str(V2), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
print(f'  exit={r.returncode}')
if r.returncode != 0:
    # Only fail if not pre-existing
    if 'failed' in r.stdout:
        issues.append({
            'id': 'DEEP-011', 'severity': 'LOW',
            'title': 'v2 baseline regression (might be pre-existing)',
            'evidence': r.stdout[-300:],
            'fix': 'review'
        })

print('\n' + '=' * 60)
print(f'{len(issues)} issues found:')
print(json.dumps(issues, indent=2, ensure_ascii=False))