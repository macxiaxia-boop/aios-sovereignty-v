"""check_pa_loop_v3.py — find PA matching loopback-demo via file scan."""
import json
import os

text = 'loopback-demo'
# scan policy + quarantined files
candidates = [
    r'D:\AIOS\_agent-hub\policy\product_strategy.v1.json',
    r'D:\AIOS\_agent-hub\policy\strategy_index.json',
]
for path in candidates:
    if not os.path.exists(path):
        continue
    print(f'scanning {path}')
    with open(path) as f:
        try:
            policy = json.load(f)
        except Exception as e:
            print(f'  parse error: {e}')
            continue
    for pa in policy.get('prohibited_active_assets', []):
        s = pa.get('summary', '')
        tokens = s.split()[:3]
        fingerprint = ' '.join(tokens)
        if fingerprint in text:
            print(f'  {pa["id"]}: fingerprint={fingerprint!r}')
            print(f'    summary: {s!r}')