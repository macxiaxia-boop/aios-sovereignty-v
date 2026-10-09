"""manual_test_dump.py — Manual generic envelope -> GoalContract cache dump (G002)."""
import sys
import os
import tempfile
import json

sys.path.insert(0, 'D:/AIOS/kernel/src')
sys.path.insert(0, 'D:/AIOS/_agent-hub/v2')

v2_root = tempfile.mkdtemp(prefix='aiosv2_g002_manual_')
os.environ['AIOS_V2_ROOT'] = v2_root

from src.inbound_goal_generation import process_inbound_envelope

env = {
    'id': 'manual-test-env-001',
    'sender': 'claudecode',
    'message_type': 'message',
    'payload': {
        'text': 'Investigate why the goal guard hook is not blocking malformed envelopes',
        'title': 'Investigate goal guard hook',
    }
}
goal, allowed, risk, cache_path = process_inbound_envelope(env, v2_root=v2_root)
print('=== Manual Generic Envelope Test (G002 acceptance evidence) ===')
print('envelope_id:', env['id'])
print('goal_id:    ', goal.id)
print('allowed:    ', allowed)
print('risk:       ', risk)
print('cache_path: ', cache_path)
print()

data = json.loads(cache_path.read_text(encoding='utf-8'))
print('=== Cache File Dump (key fields) ===')
for k, v in data.items():
    if k in ('description', 'title', 'success_criteria', 'owner', 'status', 'inferred_intent'):
        print(f'{k}: {v}')
    elif k == 'metadata':
        print(f'{k}: {v}')
    elif k in ('preserve_capabilities', 'known_constraints', 'failure_modes', 'autonomous_scope', 'requires_authorization'):
        print(f'{k}: {len(v) if isinstance(v, list) else v} entries')
    elif k == 'permission_scope':
        print(f'{k}:')
        print(f'  allowed_paths={v.get("allowed_paths", [])}')
        print(f'  max_budget={v.get("max_budget")}')
        print(f'  max_duration_sec={v.get("max_duration_sec")}')
    elif k == 'environment_context':
        print(f'{k}:')
        print(f'  cwd={v.get("cwd")}')
        print(f'  os={v.get("os")[:50]}...')
        print(f'  history_refs={v.get("history_refs")}')
print()
print('_cached_at:    ', data.get('_cached_at'))
print('_source_module:', data.get('_source_module'))
