"""R284 · surgical path replacement in start_v22_watchdog.bat
Preserves LF endings + GBK encoding (binary-safe). Idempotent.
"""
import sys
from pathlib import Path

BAT = Path(r"D:/AIOS/cloudtech-saas/start_v22_watchdog.bat")
OLD = rb"D:\AIOS\_venv312\Scripts\pythonw.exe"
NEW = rb"D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\pythonw.exe"

data = BAT.read_bytes()
n_old = data.count(OLD)
print(f"Old path occurrences in bat: {n_old}")

if n_old == 0:
    print("Already replaced · nothing to do · exit 0")
    sys.exit(0)

assert n_old == 1, f"Expected exactly 1 occurrence, found {n_old}"

# Capture pre-state metrics
lf_pre = data.count(b"\n")
crlf_pre = data.count(b"\r\n")
size_pre = len(data)

new_data = data.replace(OLD, NEW)
assert NEW in new_data
assert OLD not in new_data

# Verify byte counts preserved
assert len(new_data) - len(data) == len(NEW) - len(OLD), "Size delta wrong"
assert new_data.count(b"\n") == lf_pre, "LF count changed"
assert new_data.count(b"\r\n") == crlf_pre, "CRLF count changed"

BAT.write_bytes(new_data)

# Post-verify
data2 = BAT.read_bytes()
assert data2 == new_data, "Round-trip mismatch"
assert OLD not in data2
assert NEW in data2
print(f"OK · bat updated · LF={data2.count(bytes([10]))} · CRLF={data2.count(bytes([13,10]))} · size={len(data2)}")
print(f"size delta: {len(new_data) - size_pre} bytes (expected {len(NEW) - len(OLD)})")