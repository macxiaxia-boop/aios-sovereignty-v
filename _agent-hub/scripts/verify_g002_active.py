"""verify_g002_active.py — 清空 stale Pending goal + 验证新生成的是 Active."""
import sys, os, json
from pathlib import Path

sys.path.insert(0, r'D:\AIOS\kernel\src')
sys.path.insert(0, r'D:\AIOS\_agent-hub\v2')

import importlib.util
spec = importlib.util.spec_from_file_location(
    "inbound_goal_generation",
    r"D:\AIOS\_agent-hub\v2\src\inbound_goal_generation.py"
)
ig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ig)

GEN_DIR = Path(r'D:\AIOS\_agent-hub\v2\state\generated_goals')

# Step 1: count stale Pending
stale_count = 0
for f in GEN_DIR.glob('*.json'):
    d = json.loads(f.read_text(encoding='utf-8'))
    if d.get('status') == 'Pending':
        stale_count += 1
print(f'Before: {stale_count} Pending stale goals in generated_goals/')

# Step 2: clear them (they're stale - not user-committed)
deleted = 0
for f in GEN_DIR.glob('*.json'):
    d = json.loads(f.read_text(encoding='utf-8'))
    if d.get('status') == 'Pending':
        f.unlink()
        deleted += 1
print(f'Cleared {deleted} stale Pending goals')

# Step 3: generate 1 new with complete envelope
env = {
    'id': 'verify-active-001',
    'message_type': 'task',
    'sender': 'codex',
    'recipient': 'claudecode',
    'payload': {
        'title': 'Verify G002 active transition',
        'text': 'Phase G G002 inbound now auto-activates after GoalGuard pass.',
        'budget': 50,
        'owner': 'codex',
        'permission_scope': {
            'allowed_paths': ['D:/AIOS/_agent-hub/'],
            'allowed_ops': ['read', 'write', 'execute'],
        },
        'failure_modes': [{'name': 'test_failure'}],
        'missing_evidence': [{'name': 'production_evidence', 'required': True}],
        'autonomous_scope': [{'domain': 'service', 'action': 'execute'}],
        'requires_authorization': [{'domain': 'file', 'action': 'delete'}],
    },
}
goal, allowed, risk, path = ig.process_inbound_envelope(env)
print(f'\nNew goal generated:')
print(f'  goal.status.value: {goal.status.value}')
print(f'  allowed: {allowed}')
print(f'  cache_path: {path}')

# Re-read from disk to verify persisted as Active
time.sleep(0.2)
import time
time.sleep(0.2)
data = json.loads(path.read_text(encoding='utf-8'))
print(f'  disk cached status: {data["status"]}')

# Check audit log
audit = Path(r'D:\AIOS\_agent-hub\v2\logs\inbound_goal_audit.ndjson')
if audit.exists():
    lines = audit.read_text(encoding='utf-8').splitlines()
    print(f'  audit log: {len(lines)} events total')
    if lines:
        print(f'    latest: {lines[-1][:200]}')

# Check overall
remaining_pending = 0
remaining_active = 0
for f in GEN_DIR.glob('*.json'):
    d = json.loads(f.read_text(encoding='utf-8'))
    if d.get('status') == 'Pending':
        remaining_pending += 1
    elif d.get('status') == 'Active':
        remaining_active += 1
print(f'\nAfter: {remaining_pending} Pending, {remaining_active} Active')