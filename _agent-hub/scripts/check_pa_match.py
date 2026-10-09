"""check_pa_match.py — directly test _scan_for_prohibited_assets."""
import json

with open('D:\AIOS\_agent-hub\policy\product_strategy.v1.json') as f:
    policy = json.load(f)

text = 'loopback-demo'
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
print()

# Reimplement _scan_for_prohibited_assets logic exactly
print('Reimplement _scan_for_prohibited_assets:')
for pa in policy.get('prohibited_active_assets', []):
    pa_id = pa.get('id', '')
    summary = pa.get('summary', '') or ''
    tokens = summary.split()[:3]
    if len(tokens) < 2:
        continue
    fingerprint = ' '.join(tokens)
    if fingerprint in text:
        print(f'  HIT: pa_id={pa_id} fingerprint={fingerprint!r}')