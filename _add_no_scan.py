#!/usr/bin/env python3
"""Add --no-scan flag to reconciler.py for fast test mode"""
from pathlib import Path
fp = Path(r'D:\AIOS\_agent-hub\policy\reconciler\reconciler.py')
text = fp.read_text(encoding='utf-8')

# Add --no-scan arg
old = '    ap.add_argument("--once", action="store_true")'
new = '''    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-scan", action="store_true",
                    help="Skip slow scans (profile files) for fast test/audit mode")'''
if '--no-scan' not in text and old in text:
    text = text.replace(old, new)
    print("OK: --no-scan arg added")

# Skip profile scan if --no-scan
old_main = '''    procs = scan_processes()
    envs = scan_env()
    profiles = scan_profile_files()'''
new_main = '''    procs = scan_processes()
    envs = scan_env()
    if args.no_scan:
        profiles = []
    else:
        profiles = scan_profile_files()'''
if 'if args.no_scan:' not in text and old_main in text:
    text = text.replace(old_main, new_main)
    print("OK: --no-scan skip logic added")

fp.write_text(text, encoding='utf-8')
print("DONE")
