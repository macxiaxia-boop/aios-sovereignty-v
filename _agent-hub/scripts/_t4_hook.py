import os, hashlib, stat

HOOK = r"D:\AIOS\.git\hooks\pre-commit"

content_lines = []
content_lines.append("#!/bin/sh")
content_lines.append("# R1348C pre-commit gate: verify EXT-D 4 adapter before commit")
content_lines.append("# Added 2026-10-10 - T4 P1")
content_lines.append("# If verify_ext_d fails, abort the commit to prevent bad adapters_registry from being committed.")
content_lines.append("python D:/AIOS/_agent-hub/scripts/verify_ext_d.py")
content_lines.append('if [ $? -ne 0 ]; then')
content_lines.append('  echo "[FATAL] EXT-D adapter verify failed. Aborting commit."')
content_lines.append("  exit 1")
content_lines.append("fi")
content_lines.append("")
content = chr(10).join(content_lines)

os.makedirs(os.path.dirname(HOOK), exist_ok=True)

if os.path.exists(HOOK):
    existing = open(HOOK, encoding="utf-8").read()
    if existing == content:
        print("hook already correct, no change")
    else:
        bak = HOOK + ".pre_ext_d.bak"
        if not os.path.exists(bak):
            with open(HOOK, "rb") as f:
                old = f.read()
            with open(bak, "wb") as f:
                f.write(old)
            print("backed up existing to:", bak)
        with open(HOOK, "w", newline="", encoding="utf-8") as f:
            f.write(content)
        print("hook replaced")
else:
    with open(HOOK, "w", newline="", encoding="utf-8") as f:
        f.write(content)
    print("hook created new")

# chmod +x
try:
    st = os.stat(HOOK)
    os.chmod(HOOK, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print("chmod +x OK")
except (AttributeError, OSError) as e:
    print("chmod skipped:", e)

# Test: run verify_ext_d standalone to confirm it's still OK
import subprocess
print()
print("=== verify_ext_d smoke (drives the hook) ===")
r = subprocess.run(["python", r"D:\AIOS\_agent-hub\scripts\verify_ext_d.py"], capture_output=True, text=True, shell=False)
print("rc:", r.returncode)
print("output:", r.stdout[:200])

print()
print("=== final hook file ===")
print(f"size: {os.path.getsize(HOOK)}B")
print(f"sha: {hashlib.sha256(open(HOOK, 'rb').read()).hexdigest().upper()}")
print("---content---")
print(open(HOOK, encoding="utf-8").read())
