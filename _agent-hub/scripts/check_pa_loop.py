"""check_pa_loop.py — find PA that contains 'loop'."""
import json
with open(r'D:\AIOS\_agent-hub\policy\product_strategy.v1.json') as f:
    policy = json.load(f)
for pa in policy.get('prohibited_active_assets', []):
    s = pa.get('summary', '')
    if 'loop' in s.lower():
        tokens = s.split()[:3]
        fingerprint = ' '.join(tokens)
        print(f"{pa['id']}: summary={s!r}")
        print(f'  first 3 tokens: {tokens}')
        print(f'  fingerprint: {fingerprint!r}')
        print(f'  fingerprint in "loopback-demo": {fingerprint in "loopback-demo"}')