"""check_pa_match_v4.py — direct check after clearing."""
import sys
sys.path.insert(0, r'D:/AIOS/_agent-hub')
import json

with open(r'D:\AIOS\_agent-hub\policy\product_strategy.v1.json') as f:
    policy = json.load(f)

text = 'loopback-demo'
print('=== Direct fingerprint match check ===')
for pa in policy.get('prohibited_active_assets', []):
    s = pa.get('summary', '')
    tokens = s.split()[:3]
    fingerprint = ' '.join(tokens)
    if fingerprint in text:
        print(f'MATCH: PA={pa["id"]} fingerprint={fingerprint!r}')

print()
print('=== evaluate_envelope output ===')
from policy.strategy_gate import StrategyGate
gate = StrategyGate(policy)
result = gate.evaluate_envelope({'message_type': 'task', 'id': 'test', 'sender': 'codex', 'recipient': 'claudecode', 'payload': {'title': 'loopback-demo', 'text': 'demo'}})
for e in result.events:
    print(f'  {e.event_type}: matched_id={e.matched_id!r} matched_token={e.matched_token!r}')
    print(f'    message: {e.message[:200]}')