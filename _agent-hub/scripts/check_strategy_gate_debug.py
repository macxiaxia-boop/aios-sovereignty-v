"""check_strategy_gate_debug.py — debug which PA matches loopback-demo."""
import sys
sys.path.insert(0, r'D:\AIOS\_agent-hub\policy')
import json
from policy.strategy_gate import StrategyGate

with open(r'D:\AIOS\_agent-hub\policy\product_strategy.v1.json') as f:
    policy = json.load(f)

text = 'loopback-demo'
print('PA summary first-3-token fingerprint matches:')
for pa in policy.get('prohibited_active_assets', []):
    s = pa.get('summary', '')
    tokens = s.split()[:3]
    fingerprint = ' '.join(tokens)
    if fingerprint in text:
        print(f'  {pa["id"]}: fingerprint={fingerprint!r}')

# Patch _scan_for_prohibited_assets to log
import policy.strategy_gate as sg
orig = sg.StrategyGate._scan_for_prohibited_assets
def traced(self, text):
    print(f'_scan_for_prohibited_assets called with text={text!r}')
    for pa in self.policy.get('prohibited_active_assets', []):
        pa_id = pa.get('id', '')
        summary = pa.get('summary', '') or ''
        tokens = summary.split()[:3]
        if len(tokens) < 2:
            continue
        fingerprint = ' '.join(tokens)
        if fingerprint in text:
            print(f'  matched PA={pa_id} fingerprint={fingerprint!r}')
    return orig(self, text)
sg.StrategyGate._scan_for_prohibited_assets = traced

gate = StrategyGate(policy)
result = gate.evaluate_envelope({'message_type': 'task', 'id': 'test', 'sender': 'codex', 'recipient': 'claudecode', 'payload': {'title': 'loopback-demo', 'text': 'demo'}})
print(f'\nresult.allowed = {result.allowed}')
for e in result.events:
    print(f'  {e.event_type}: matched_token={e.matched_token!r} matched_id={e.matched_id}')