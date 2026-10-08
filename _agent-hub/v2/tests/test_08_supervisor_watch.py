# v2/tests/test_08_supervisor_watch.py
# Acceptance: supervisor/watch 可用 (完工标准 F)
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "aiosv2.py"


def run_cli(*args, timeout=30):
    p = subprocess.run([sys.executable, str(CLI)] + list(args),
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def test_cli_tick_runs_and_returns_reaped_snapshot():
    rc, out, err = run_cli("tick")
    assert rc == 0, err
    j = json.loads(out)
    assert "snapshot_tasks" in j
    assert "snapshot_counters" in j


def test_cli_watch_runs_two_ticks_then_exits():
    # watch with --max-ticks 2 and --interval 0.1 should print 2 lines and exit
    proc = subprocess.run([sys.executable, str(CLI), "watch",
                           "--interval", "0.1", "--max-ticks", "2"],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0
    # At least 2 non-empty lines
    lines = [l for l in proc.stdout.splitlines() if l.strip().startswith("{")]
    assert len(lines) >= 2
    # Each line must be valid JSON
    for l in lines:
        json.loads(l)