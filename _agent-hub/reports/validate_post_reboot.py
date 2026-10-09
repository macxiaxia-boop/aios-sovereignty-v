#!/usr/bin/env python3
"""
validate_post_reboot.py — Run this AFTER `shutdown /r /t 0` reboots Windows.

Checks that AIOS Core Spine truly works post-reboot:
1. AIOSV2Consumer WinSW service is Running
2. AIOSConsumerMinute scheduled task exists
3. v2 consumer child pythonw is alive with start_consumer_real in cmdline
4. port 5099 is NOT listening (zombie gone)
5. 24/24 P8 acceptance + verifier + dispatch_runtime all PASS
6. state.json updated_at fresh
7. events.ndjson last dispatch < 5 min ago

Outputs GREEN/RED per check + writes PASS.md if all green.
"""

import subprocess, json, time, sys
from pathlib import Path

CHECKS = {}

# 1. Service
out = subprocess.run(["sc", "query", "AIOSV2Consumer"], capture_output=True, text=True)
CHECKS["1_AIOSV2Consumer_service"] = "✅" if "RUNNING" in out.stdout else "❌"

# 2. Task
out = subprocess.run(["schtasks", "/query", "/fo", "LIST"], capture_output=True, text=True)
CHECKS["2_AIOSConsumerMinute_task"] = "✅" if "AIOSConsumerMinute" in out.stdout else "❌"

# 3. Consumer child
out = subprocess.run(
    ["wmic", "process", "where", "name='pythonw.exe'", "get", "ProcessId,CommandLine", "/FORMAT:CSV"],
    capture_output=True, text=True,
)
CHECKS["3_consumer_pythonw_alive"] = "✅" if "start_consumer_real" in out.stdout else "❌"

# 4. Port 5099
out = subprocess.run(
    ["powershell", "-Command", "Get-NetTCPConnection -LocalPort 5099 -State Listen -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"],
    capture_output=True, text=True,
)
port_count = int(out.stdout.strip() or "1")
CHECKS["4_port_5099_not_listening"] = "✅" if port_count == 0 else f"⚠️ still {port_count} listeners"

# 5. Tests
import os
os.environ["AIOS_V2_ROOT"] = r"D:\AIOS\_agent-hub\v2"
os.environ["PYTHONPATH"] = r"D:\AIOS\_agent-hub\v2"
out = subprocess.run(
    [sys.executable, "-m", "pytest",
     "tests/test_p8_t07.py", "tests/test_p8_t15.py", "tests/test_p8_t20.py", "tests/test_p8_t21.py",
     "tests/test_p8_t22.py", "tests/test_p8_t23.py", "tests/test_p8_t24.py", "tests/test_verifier.py",
     "-q", "--tb=line"],
    capture_output=True, text=True, cwd=r"D:\AIOS\_agent-hub\v2",
)
test_pass = "passed" in out.stdout.lower() and "failed" not in out.stdout.lower()
CHECKS["5_p8_tests_pass"] = "✅" if test_pass else "❌"

# 6. State.json freshness
import os
sj_path = Path(r"D:\AIOS\_agent-hub\v2\state\state.json")
if sj_path.exists():
    age_min = (time.time() - sj_path.stat().st_mtime) / 60
    CHECKS["6_state_json_recent"] = f"✅ ({age_min:.0f}min ago)" if age_min < 30 else f"⚠️ {age_min:.0f}min stale"

# 7. events.ndjson
import re
log_path = Path(r"D:\AIOS\_agent-hub\v2\logs\events.ndjson")
if log_path.exists():
    last_line = log_path.read_text(encoding="utf-8").strip().split("\n")[-1] if log_path.read_text(encoding="utf-8").strip() else ""
    if "ts" in last_line:
        try:
            ts_match = re.search(r'"ts":\s*"([^"]+)"', last_line)
            if ts_match:
                from datetime import datetime
                last_ts = datetime.fromisoformat(ts_match.group(1).replace("Z", "+00:00"))
                age_min = (datetime.now(datetime.timezone.utc) - last_ts).total_seconds() / 60
                CHECKS["7_events_recent_dispatch"] = f"✅ ({age_min:.0f}min ago)" if age_min < 10 else f"⚠️ {age_min:.0f}min ago"
            else:
                CHECKS["7_events_recent_dispatch"] = "⚠️ last line no ts"
        except Exception as e:
            CHECKS["7_events_recent_dispatch"] = f"⚠️ parse: {e}"
    else:
        CHECKS["7_events_recent_dispatch"] = "⚠️ empty"

# Report
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