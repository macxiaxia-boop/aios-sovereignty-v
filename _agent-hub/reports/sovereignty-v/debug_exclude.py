import json
from pathlib import Path
from collections import Counter

EXCLUDED = {
    '__pycache__', '.git', '.venv', 'venv', 'node_modules', '.cache',
    '.uv-cache', 'uv-cache', '.tox', '.eggs', 'dist', 'build',
    '.next', '.nuxt', '.output', 'coverage', '.nyc_output',
    '_backups', 'backups', 'legacy',
    'dist-v45', 'dist-v4', 'dist-v3',
    'design/research/references',
    'shadcn-ui',
    'attachments', 'computer-use',
    'hermes-agent', '_archive-sessions', 'cache', '_backup',
    'model-policy.v1', 'codex_adapter.py', 'cloudtech_pre_tool_use_hook.py',
    'reconciler.py', 'adapter-contract.md', 'adapter-spec.v1.md',
    'acceptance_phase_i', 'audit_gap_check', 'W14_', 'spec',
}

with open(r'D:\AIOS\_agent-hub\audit\drift-events.log', 'r', encoding='utf-8') as f:
    lines = [l for l in f if l.strip()]
e = json.loads(lines[-1])

remaining = []
for d in e['drift']:
    p = d['path']
    p_norm = p.replace('\\', '/')
    parts = Path(p_norm).parts
    excluded = any(tag in parts for tag in EXCLUDED)
    if not excluded:
        remaining.append(d)

print(f'v7 remaining: {len(remaining)}')
print()
print('top user paths remaining:')
ct = Counter()
for d in remaining:
    p = d['path'].replace('\\', '/')
    parts = Path(p).parts
    if 'Users' in p:
        ct['/'.join(parts[2:5])] += 1
for k, v in ct.most_common(25):
    print(f'  {v:>4} {k}')
