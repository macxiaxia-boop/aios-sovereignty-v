"""check_pa_match_v2.py — fix path escape."""
import json
import os

text = 'loopback-demo'
policy_path = r'D:/AIOS/_agent-hub/policy/product_strategy.v1.json'
print(f'loading {policy_path}')
with open(policy_path) as f:
    policy = json.load(f)

print('PA fingerprints (first-3-tokens):')
matches = []
for pa in policy.get('prohibited_active_assets', []):
    s = pa.get('summary', '')
    tokens = s.split()[:3]
    fingerprint = ' '.join(tokens)
    in_text = fingerprint in text
    if in_text:
        matches.append((pa['id'], fingerprint, s))
        print(f'  MATCH {pa["id"]}: fingerprint={fingerprint!r}')

if not matches:
    print('  No direct fingerprint match.')

# Now check actual evaluate_envelope output
import sys
sys.path.insert(0, r'D:/AIOS/_agent-hub/policy')
from strategy_gate import StrategyGate

gate = StrategyGate(policy)
result = gate.evaluate_envelope({'message_type': 'task', 'id': 'test', 'sender': 'codex', 'recipient': 'claudecode', 'payload': {'title': 'loopback-demo', 'text': 'demo'}})
print(f'\nevaluate_envelope result: allowed={result.allowed}')
for e in result.events:
    print(f'  {e.event_type}: matched_id={e.matched_id!r}')