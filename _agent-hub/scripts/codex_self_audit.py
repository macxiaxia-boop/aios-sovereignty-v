#!/usr/bin/env python3
r"""codex_self_audit.py — Codex Supervisor 自审计（autonomous）。

退出码：0=CLEAN, 1=DEGRADED, 2=BROKEN

Phase F + Phase-2/3 后 baseline：
- v2 consumer 已从 python 进程改为 Windows Service (AIOSV2Consumer, Phase-2)
- 查 service 状态 (sc query AIOSV2Consumer) 而非 python process
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

AIOS_ROOT = Path("D:/AIOS")
KERNEL_ROOT = AIOS_ROOT / "kernel"
MEMORY_DIR = AIOS_ROOT / "_agent-hub" / "memory"
TODAY = datetime.now().strftime("%Y-%m-%d")
NOW_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

AIOS_DIRTY_MAX = 500
KERNEL_DIRTY_MAX = 100


def banner(t):
    print(f"\n=== {t} ===")


def run(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"TIMEOUT after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def check_preflight():
    banner("preflight v4")
    code, out, err = run(
        [sys.executable, str(AIOS_ROOT / "aios_tasks" / "aios_vnext" / "preflight_check.py")],
        cwd=AIOS_ROOT / "aios_tasks" / "aios_vnext", timeout=30,
    )
    is_clean = "CLEAN" in out
    print(f"exit={code} clean={is_clean}")
    return (0 if is_clean else 1), out


def check_pytest_baseline():
    banner("pytest baseline (kernel unit)")
    py = KERNEL_ROOT / ".venv" / "Scripts" / "python.exe"
    if not py.exists():
        return 1, "python venv not found"
    code, out, err = run(
        [str(py), "-m", "pytest",
         "tests/unit/test_goal_schema.py",
         "tests/unit/test_decision_audit.py",
         "tests/unit/test_intent_parser.py",
         "tests/unit/test_failure_pattern_merger.py",
         "tests/unit/test_goal_guard.py",
         "tests/unit/test_plan_versioning.py",
         "--tb=no", "-q", "--no-header"],
        cwd=KERNEL_ROOT, timeout=300,
    )
    summary = ""
    for line in (out + err).splitlines():
        if ("passed" in line or "failed" in line or "error" in line) and "==" not in line:
            summary = line.strip()
            break
    print(f"kernel exit={code} summary={summary}")
    return code, summary


def check_v2_consumer_health():
    """Phase-2: v2 consumer 已注册为 Windows Service AIOSV2Consumer。检查服务状态。"""
    banner("v2 consumer (Windows Service AIOSV2Consumer)")
    code, out, err = run(["sc", "query", "AIOSV2Consumer"], timeout=15)
    # parse STATE field
    is_running = False
    is_installed = False
    state_line = ""
    for line in out.splitlines():
        if "SERVICE_NAME" in line and "AIOSV2Consumer" in line:
            is_installed = True
        if line.strip().startswith("STATE"):
            state_line = line.strip()
            # "STATE              : 4  RUNNING"
            if "RUNNING" in line:
                is_running = True
    msg = f"installed={is_installed} state={state_line} running={is_running}"
    print(msg)
    return (0 if is_running else 1), msg


def check_git_dirty():
    banner("git dirty count")
    ai_code, ai_out, _ = run(["git", "status", "--short"], cwd=AIOS_ROOT, timeout=15)
    kr_code, kr_out, _ = run(["git", "status", "--short"], cwd=KERNEL_ROOT, timeout=15)
    ai_count = len([l for l in ai_out.splitlines() if l.strip()])
    kr_count = len([l for l in kr_out.splitlines() if l.strip()])
    ai_ok = ai_count < AIOS_DIRTY_MAX
    kr_ok = kr_count < KERNEL_DIRTY_MAX
    msg = f"AIOS={ai_count} (max {AIOS_DIRTY_MAX}) kernel={kr_count} (max {KERNEL_DIRTY_MAX})"
    print(msg)
    return (0 if ai_ok and kr_ok else 1), msg


def write_self_audit_log(preflight_code, pytest_code, v2_code, git_code, findings):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    memory_file = MEMORY_DIR / f"{TODAY}.md"
    status = "CLEAN" if all(c == 0 for c in [preflight_code, pytest_code, v2_code, git_code]) else "DEGRADED"
    section = f"""

## {NOW_ISO[11:16]} Codex Self-Audit ({status})

| 检查 | 退出码 | 状态 |
|---|---|---|
| preflight v4 | {preflight_code} | {'OK' if preflight_code == 0 else 'WARN'} |
| pytest baseline | {pytest_code} | {'OK' if pytest_code == 0 else 'WARN'} |
| v2 consumer | {v2_code} | {'OK' if v2_code == 0 else 'WARN'} |
| git dirty | {git_code} | {'OK' if git_code == 0 else 'WARN'} |

"""
    if findings:
        section += "**Findings**:\n"
        for f in findings:
            section += f"- {f}\n"
    with open(memory_file, "a", encoding="utf-8") as f:
        f.write(section)
    print(f"self-audit 写入 {memory_file}")


def main():
    print(f"# Codex Self-Audit @ {NOW_ISO}")
    preflight_code, _ = check_preflight()
    pytest_code, pytest_summary = check_pytest_baseline()
    v2_code, _ = check_v2_consumer_health()
    git_code, git_msg = check_git_dirty()

    findings = []
    if preflight_code != 0:
        findings.append("preflight dirty: 今日有 forbidden 文件")
    if pytest_code != 0:
        findings.append(f"pytest baseline 退化: {pytest_summary}")
    if v2_code != 0:
        findings.append("v2 consumer (AIOSV2Consumer Windows Service) 不在 RUNNING")
    if git_code != 0:
        findings.append(f"git dirty 超阈值: {git_msg}")

    overall = max(preflight_code, pytest_code, v2_code, git_code)
    write_self_audit_log(preflight_code, pytest_code, v2_code, git_code, findings)
    banner(f"OVERALL: {'CLEAN' if overall == 0 else 'DEGRADED'}")
    print(f"exit={overall}")
    return overall


if __name__ == "__main__":
    sys.exit(main())