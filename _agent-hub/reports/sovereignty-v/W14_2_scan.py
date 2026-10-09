import os, re
from pathlib import Path

EXCLUDE = {'__pycache__', '.git', '.venv', 'venv', 'node_modules', '.cache', '.tox', '.eggs',
           'dist', 'build', '.next', '.nuxt', '.output', 'coverage', '.nyc_output',
           '_backups'}

found = []
for p in Path('D:/CloudTech-Portable').rglob('*.py'):
    if any(part in EXCLUDE for part in p.parts):
        continue
    if p.stat().st_size > 200000:
        continue
    try:
        content = p.read_text(encoding='utf-8', errors='ignore')
    except:
        continue
    has_key = bool(re.search(r'(DEEPSEEK_API_KEY|DEEPSEEK_KEY)\s*=\s*', content))
    has_call = 'deepseek_call(' in content or 'deepseek-chat' in content or 'deepseek-v4' in content
    if has_key and has_call:
        found.append({'path': str(p), 'size': p.stat().st_size})

print(f'active DeepSeek-using files (excluding _backups): {len(found)}')
for f in found[:20]:
    print(f"  {f['size']:>8,d}  {f['path']}")