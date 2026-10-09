"""check_aliases.py — find what aliases loopback-demo matches."""
import json

with open(r'D:/AIOS/_agent-hub/policy/product_strategy.v1.json') as f:
    policy = json.load(f)

text = 'loopback-demo'

# search all dict/list fields for 'loop'
def search(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            search(v, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            search(v, f'{path}[{i}]')
    elif isinstance(o, str):
        if 'loop' in o.lower() and len(o) < 80:
            # Check if text is in 'loopback-demo'
            for tok in o.split():
                if tok in text:
                    print(f'  match: {path}: token={tok!r} in full={o!r}')

print('=== policy contains loop-related tokens matching loopback-demo ===')
search(policy)
print('=== end ===')