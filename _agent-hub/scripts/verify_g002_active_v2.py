"""verify_g002_active_v2.py — G002 active transition end-to-end."""
import sys, json, time
sys.path.insert(0, r'D:\AIOS\kernel\src')
sys.path.insert(0, r'D:\AIOS\_agent-hub\v2')

import importlib.util
spec = importlib.util.spec_from_file_location(
    'ig', r'D:\AIOS\_agent-hub\v2\src\inbound_goal_generation.py'
)
ig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ig)

env = {
    'id': 'verify-active-final',
    'message_type': 'task',
    'sender': 'codex',
    'recipient': 'claudecode',
    'payload': {
        'title': 'Verify G002 active transition',
        'text': 'Phase G G002 inbound auto-activates after GoalGuard pass.',
        'budget': 0.01,
        'owner': 'codex',
        'allowed_paths': ['D:/AIOS/_agent-hub/'],
        'allowed_ops': ['read','write','execute'],
        'max_duration_sec': 300,
        'failure_modes': [{'description': 'test_failure', 'detection': 'pytest fail'}],
        'missing_evidence': [{'description': 'production_evidence', 'source': 'production', 'required': True}],
        'autonomous_scope': [{'domain': 'service', 'action': 'execute'}],
        'requires_authorization': [{'domain': 'file', 'action': 'delete'}],
    },
}
goal, allowed, risk, path = ig.process_inbound_envelope(env)
print(f'allowed: {allowed}')
print(f'goal.status.value: {goal.status.value}')
print(f'goal.budget: {goal.budget}, perm.max_budget: {goal.permission_scope.max_budget}')
time.sleep(0.2)
data = json.loads(path.read_text(encoding='utf-8'))
print(f'disk cached status: {data["status"]}')
print(f'disk cached budget/perm_max_budget: {data["budget"]}/{data["permission_scope"]["max_budget"]}')
print()
audit = r'D:\AIOS\_agent-hub\v2\logs\inbound_goal_audit.ndjson'
import os
if os.path.exists(audit):
    lines = open(audit).readlines()
    print(f'audit events: {len(lines)}')
    if lines:
        print(f'  latest: {lines[-1][:250]}')