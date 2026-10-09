#!/usr/bin/env python3
"""Clear non-MiniMax env credentials from HKCU\Environment + current process.
SOVEREIGNTY-V full audit, user authorized 2026-10-09.
"""
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
import ctypes
from ctypes import wintypes

VARS = ['QWEN_API_KEY', 'DASHSCOPE_API_KEY', 'AGNES_API_KEY', 'ZHIPU_API_KEY']
AUDIT_LOG = Path(r'D:\AIOS\_agent-hub\audit\env-credential-clears.log')
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
    f.write(f"\n[{ts}] [Codex-01a11c23-SovereigntyV-FullAudit] BEG env credential purge (user authorized)\n")

# 1) Read current values for audit
def get_reg_value(name, hive='HKCU', subkey='Environment'):
    """Read registry value via reg.exe"""
    try:
        r = subprocess.run(
            ['reg', 'query', f'{hive}\\{subkey}', '/v', name],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.splitlines():
            if name in line and 'REG_' in line:
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    return parts[2]
    except Exception:
        pass
    return None

def delete_reg_value(name, hive='HKCU', subkey='Environment'):
    """Delete registry value via reg.exe"""
    try:
        r = subprocess.run(
            ['reg', 'delete', f'{hive}\\{subkey}', '/v', name, '/f'],
            capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0
    except Exception as e:
        return False

results = {}
for var in VARS:
    print(f"\n=== {var} ===")
    old_reg = get_reg_value(var)
    old_proc = os.environ.get(var)
    old_reg_masked = (old_reg[:12] + '...') if old_reg else '<NOT_SET>'
    old_proc_masked = (old_proc[:12] + '...') if old_proc else '<NOT_SET>'

    # Delete from HKCU\Environment
    deleted = delete_reg_value(var)
    # Unset in current process
    if var in os.environ:
        del os.environ[var]
    # Also via Windows API for current process (more thorough)
    try:
        ctypes.windll.kernel32.SetEnvironmentVariableW(var, None)
    except Exception:
        pass

    after_reg = get_reg_value(var)
    after_proc = os.environ.get(var)
    after_reg_disp = after_reg if after_reg else '<CLEARED>'
    after_proc_disp = after_proc if after_proc else '<CLEARED>'

    audit_line = f"[{ts}] CLEARED {var}: HKCU={old_reg_masked} -> {after_reg_disp} | Process={old_proc_masked} -> {after_proc_disp} | reg_delete={deleted}"
    with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
        f.write(audit_line + "\n")
    print(f"  HKCU: {old_reg_masked} -> {after_reg_disp} (delete={deleted})")
    print(f"  Process: {old_proc_masked} -> {after_proc_disp}")
    print(f"  audit: {audit_line}")
    results[var] = (old_reg, after_reg, old_proc, after_proc, deleted)

# 2) Broadcast env change to running processes (Windows: WM_SETTINGCHANGE)
try:
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    user32 = ctypes.windll.user32
    res = user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 5000, None)
    broadcast_ok = res != 0
    print(f"\n=== Broadcast: result={res} ({'OK' if broadcast_ok else 'FAILED'}) ===")
except Exception as e:
    broadcast_ok = False
    print(f"\n=== Broadcast: FAILED {e} ===")

with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
    f.write(f"[{ts}] DONE env credential purge (4 vars) · broadcast={broadcast_ok}\n")
    # Final verify
    for var in VARS:
        reg_v = get_reg_value(var) or '<CLEARED>'
        proc_v = os.environ.get(var, '<CLEARED>')
        f.write(f"  VERIFY {var}: HKCU={reg_v} Process={proc_v}\n")

# Final summary
print("\n=== Final verification ===")
all_clear = True
for var in VARS:
    reg_v = get_reg_value(var)
    proc_v = os.environ.get(var)
    cleared = not reg_v and not proc_v
    status = "✅ CLEARED" if cleared else f"❌ STILL: HKCU={reg_v} Process={proc_v}"
    print(f"  {var}: {status}")
    if not cleared:
        all_clear = False

print(f"\nALL 4 CLEARED: {all_clear}")
print(f"Audit log: {AUDIT_LOG}")
