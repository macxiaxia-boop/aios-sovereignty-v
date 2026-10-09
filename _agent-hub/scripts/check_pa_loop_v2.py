"""check_pa_loop_v2.py — find which PA matches loopback-demo."""
import json
with open(r'D:\AIOS\_agent-hub\policy\product_strategy.v1.json') as f:
    policy = json.load(f)
text = 'loopback-demo'
for pa in policy.get('prohibited_active_assets', []):
    s = pa.get('summary', '')
    if 'loop' in s.lower():
        tokens = s.split()[:3]
        fingerprint = ' '.join(tokens)
        # Also check each token
        for t in tokens:
            if t in text:
                print(f'{pa["id"]}: token match: {t!r} in {text!r}')
                print(f'  full summary: {s!r}')
                break
        else:
            continue
        break