#!/usr/bin/env python3
"""Clear [profiles.ollama] and [profiles.qwen25] sections from C:\Users\xinzh\.codex\config.toml
Per kernel codex_adapter enforcement.profiles_legacy_cleanup: [ollama, qwen25]
"""
import re
import shutil
import time
from pathlib import Path
from datetime import datetime

CFG = Path(r'C:\Users\xinzh\.codex\config.toml')
BACKUP = Path(rf'C:\Users\xinzh\.codex\config.toml.bak-sovereignty-v-{int(time.time())}')

# 1) Backup
shutil.copy2(CFG, BACKUP)
print(f"Backup: {BACKUP} ({BACKUP.stat().st_size} B)")

# 2) Read current
text = CFG.read_text(encoding='utf-8')
original_size = len(text)
print(f"Original: {CFG} ({original_size} B)")

# 3) Strip [profiles.ollama] and [profiles.ollama.windows] blocks
def strip_block(s, block_name):
    """Strip [block_name] ... [/] (or until next [section] header)"""
    # Match [block_name] ... up to next [ at start of line
    pattern = rf'^\[{re.escape(block_name)}\].*?(?=^\[|\Z)'
    new_s, n = re.subn(pattern, '', s, flags=re.MULTILINE | re.DOTALL)
    if n > 0:
        print(f"  stripped [{block_name}] block ({n} match)")
    return new_s

for block in ['profiles.ollama.windows', 'profiles.ollama', 'profiles.qwen25.windows', 'profiles.qwen25']:
    text = strip_block(text, block)

# Clean up double blank lines
text = re.sub(r'\n\n\n+', '\n\n', text)

# 4) Write
CFG.write_text(text, encoding='utf-8')
print(f"New: {CFG} ({len(text)} B, delta={len(text)-original_size})")

# 5) Verify
print("\n=== verify profiles sections removed ===")
for line in text.splitlines():
    if line.strip().startswith('[profiles.') or line.strip().startswith('[profiles]'):
        print(f"  LEFTOVER: {line}")
print("  (if no LEFTOVER lines, clean)")

# 6) Audit log
AUDIT = Path(r'D:\AIOS\_agent-hub\audit\profile-clears.log')
AUDIT.parent.mkdir(parents=True, exist_ok=True)
ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open(AUDIT, 'a', encoding='utf-8') as f:
    f.write(f"[{ts}] CLEARED profiles.ollama + profiles.qwen25 from {CFG} | backup={BACKUP} | size_delta={len(text)-original_size}\n")
print(f"\nAudit log: {AUDIT}")
