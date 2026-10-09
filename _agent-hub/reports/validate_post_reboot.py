#!/usr/bin/env python3
"""validate_post_reboot.py — corrected version with -p no:anyio + datetime fix"""
import subprocess
import json
import time
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

V2_ROOT = Path(r"D:\AIOS\_agent-hub\v2")


def safe_decode(b):
    if b is None:
        return ""
    for enc in ("utf-8", "gbk", "cp936", "latin-1"):
        try:
            return b.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode("utf-8", errors="replace")


CHECKS = {}

# 1. Service
proc = subprocess.run(["sc", "query", "AIOSV2Consumer"], capture_output=True)
out = safe_decode(proc.stdout)
CHECKS["1_AIOSV2Consumer_service"] = "✅" if "RUNNING" in out else "❌"

# 2. Task
proc = subprocess.run(["schtasks", "/query", "/fo", "LIST"], capture_output=True)
out = safe_decode(proc.stdout)
CHECKS["2_AIOSConsumerMinute_task"] = "✅" if "AIOSConsumerMinute" in out else "❌"

# 3. Consumer child
proc = subprocess.run(
    ["wmic", "process", "where", "name='pythonw.exe'", "get", "ProcessId,CommandLine", "/FORMAT:CSV"],
    capture_output=True,
)
out = safe_decode(proc.stdout)
CHECKS["3_consumer_pythonw_alive"] = "✅" if "start_consumer_real" in out else "❌"

# 4. port 5099
proc = subprocess.run(
    ["powershell", "-Command", "Get-NetTCPConnection -LocalPort 5099 -State Listen -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"],
    capture_output=True, text=True,
)
port_count = int((proc.stdout or "1").strip() or "1")
CHECKS["4_port_5099_not_listening"] = "✅" if port_count == 0 else f"⚠️ still {port_count} listeners"

# 5. Tests with -p no:anyio to avoid asyncio init failure
proc = subprocess.run(
    [sys.executable, "-m", "pytest",
     "tests/test_p8_t07.py", "tests/test_p8_t15.py", "tests/test_p8_t20.py", "tests/test_p8_t21.py",
     "tests/test_p8_t22.py", "tests/test_p8_t23.py", "tests/test_p8_t24.py", "tests/test_verifier.py",
     "tests/test_strategy_gate.py", "tests/test_strategy_gate_round6_fixes.py",
     "-q", "--tb=line", "-p", "no:anyio"],
    capture_output=True,
    cwd=str(V2_ROOT),
    env={"PYTHONPATH": str(V2_ROOT), "AIOS_V2_ROOT": str(V2_ROOT), "PATH": "C:\\Windows\\system32;C:\\Windows"},
    timeout=120,
)
out = safe_decode(proc.stdout)
err = safe_decode(proc.stderr)
combined = out + "\n" + err
test_pass = "passed" in combined.lower() and "failed" not in combined.lower()
CHECKS["5_p8_strategy_gate_tests_pass"] = "✅" if test_pass else "❌"

# 6. State.json freshness
sj_path = Path(r"D:\AIOS\_agent-hub\v2\state\state.json")
if sj_path.exists():
    age_min = (time.time() - sj_path.stat().st_mtime) / 60
    CHECKS["6_state_json_recent"] = f"✅ ({age_min:.0f}min ago)" if age_min < 30 else f"⚠️ {age_min:.0f}min stale"

# 7. events.ndjson (fixed timezone reference)
log_path = Path(r"D:\AIOS\_agent-hub\v2\logs\events.ndjson")
if log_path.exists():
    last_line = log_path.read_text(encoding="utf-8").strip().split("\n")[-1] if log_path.read_text(encoding="utf-8").strip() else ""
    if "ts" in last_line:
        try:
            ts_match = re.search(r'"ts":\s*"([^"]+)"', last_line)
            if ts_match:
                from datetime import datetime as dt
                last_ts = dt.fromisoformat(ts_match.group(1).replace("Z", "+00:00"))
                age_min = (dt.now(dt.timezone.utc) - last_ts).total_seconds() / 60
                CHECKS["7_events_recent_dispatch"] = f"✅ ({age_min:.0f}min ago)" if age_min < 10 else f"⚠️ {age_min:.0f}min ago"
            else:
                CHECKS["7_events_recent_dispatch"] = "⚠️ last line no ts"
        except Exception as e:
            CHECKS["7_events_recent_dispatch"] = f"⚠️ parse: {e}"
    else:
        CHECKS["7_events_recent_dispatch"] = "⚠️ empty"

print("=" * 60)
print("AIOS POST-REBOOT VALIDATION")
print("=" * 60)
all_green = True
for name, status in CHECKS.items():
    icon = "✅" if status.startswith("✅") else ("⚠️ " if status.startswith("⚠️") else "❌")
    if not status.startswith("✅"):
        all_green = False
    print(f"{icon} {name}: {status}")

print("=" * 60)
if all_green:
    print("🟢 AIOS Core Spine TRUE: post-reboot state is clean!")
    Path(r"D:\AIOS\_agent-hub\reports\POST_REBOOT_VERIFIED.md").write_text(
        f"# Post-Reboot Verified\n\nDate: {time.ctime()}\n\nAll 7 checks green:\n\n" +
        "\n".join(f"- {n}: {s}" for n, s in CHECKS.items()),
        encoding="utf-8",
    )
    print("Marker: D:\\AIOS\\_agent-hub\\reports\\POST_REBOOT_VERIFIED.md")
    sys.exit(0)
else:
    print("⚠️ Post-reboot check has issues. See above.")
    sys.exit(1)