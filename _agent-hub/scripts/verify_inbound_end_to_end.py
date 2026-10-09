"""verify_inbound_end_to_end.py — 端到端验证 G002 inbound fix."""
import sys, os, json, time
from pathlib import Path

sys.path.insert(0, r'D:\AIOS\kernel\src')
sys.path.insert(0, r'D:\AIOS\_agent-hub\v2')

# bypass src package resolution by direct file path import
import importlib.util
spec = importlib.util.spec_from_file_location(
    "inbound_goal_generation",
    r"D:\AIOS\_agent-hub\v2\src\inbound_goal_generation.py"
)
ig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ig)

env = {
    'id': 'audit-test-1',
    'message_type': 'task',
    'sender': 'codex',
    'recipient': 'claudecode',
    'payload': {
        'title': 'Audit test goal',
        'text': '30 分钟内完成 Phase G 验收, 宁可慢不要出错',
        'budget': 100,
        'owner': 'codex',
        'permission_scope': {'allowed_paths': ['D:/AIOS/_agent-hub/'], 'allowed_ops': ['read','write','execute']},
        'failure_modes': [{'name': 'x'}],
        'missing_evidence': [{'name': 'y', 'required': True}],
        'autonomous_scope': [{'domain': 'a', 'action': 'b'}],
        'requires_authorization': [{'domain': 'c', 'action': 'd'}],
    }
}
goal, allowed, risk, path = ig.process_inbound_envelope(env)
print(f'allowed: {allowed}')
print(f'goal.status.value: {goal.status.value}')
print(f'cache_path: {path}')
time.sleep(0.5)
data = json.loads(path.read_text(encoding='utf-8'))
print(f'cached status: {data["status"]}')
print()
audit = Path(r'D:\AIOS\_agent-hub\v2\logs\inbound_goal_audit.ndjson')
if audit.exists():
    print('audit log (last 3 lines):')
    for line in audit.read_text(encoding='utf-8').splitlines()[-3:]:
        print(' ', line)
else:
    print('audit log not found')