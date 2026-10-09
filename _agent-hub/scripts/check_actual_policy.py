"""check_actual_policy.py — see what policy the goal_guard_hook uses."""
import sys
import os
sys.path.insert(0, r'D:/AIOS/_agent-hub')
sys.path.insert(0, r'D:/AIOS/_agent-hub/policy')
os.environ['AIOS_V2_ROOT'] = r'D:/AIOS/_agent-hub/v2'

from policy.strategy_gate import strategy_gate_for_root
gate = strategy_gate_for_root(r'D:/AIOS/_agent-hub/v2')
print(f'gate is None: {gate is None}')
if gate:
    policy = gate.policy
    print(f'policy keys: {list(policy.keys())[:8]}')
    pa_list = policy.get('prohibited_active_assets', [])
    print(f'prohibited_active_assets count: {len(pa_list)}')
    print('PA summaries:')
    for pa in pa_list:
        print(f'  {pa["id"]}: {pa.get("summary", "")!r}')