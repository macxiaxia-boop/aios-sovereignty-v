#!/usr/bin/env python3
"""
AIOS VNext Preflight Check v4 — 加 mtime 过滤，只查 CC 今日创建的新 forbidden 文件

设计原则：
- 只标"今日新创建且未在白名单位置 + 命中 forbidden 模式"
- pre-existing（任何 mtime < 今天 00:00）一律 pass
- 这是 CC 的"防协议复印病"专用工具

退出码：
  0 = clean
  1 = dirty
"""
import argparse
import fnmatch
import os
import sys
from datetime import date, datetime
from pathlib import Path


AIOS_ROOT = Path("D:/AIOS")
CARDS_DIR = AIOS_ROOT / "aios_tasks" / "aios_vnext"
EVIDENCE_DIR = CARDS_DIR / "evidence"

# 今日 00:00 作为 baseline 时间戳
TODAY_START = datetime.combine(date.today(), datetime.min.time()).timestamp()

# Static whitelist
WHITELIST_FILES = {
    "D:/AIOS/AGENTS.md",
    "D:/AIOS/_popup_system_README.md",
    "D:/AIOS/aios_tasks/aios_vnext/handoff.md",
    "D:/AIOS/aios_tasks/aios_vnext/INDEX.md",
    "D:/AIOS/aios_tasks/aios_vnext/_cc_workflow.md",
    "D:/AIOS/aios_tasks/aios_vnext/preflight_check.py",
}

# Directory whitelist — 这些目录下任何 mtime 文件都 pass
WHITELIST_DIRS = {
    "D:/AIOS/aios_tasks/aios_vnext/cards",
    "D:/AIOS/aios_tasks/aios_vnext/evidence",
    "D:/AIOS/kernel",
    "D:/AIOS/aios_tasks",
    "D:/AIOS/aios_tools",
    "D:/AIOS/aios_venv",
    "D:/AIOS/_archived",
    "D:/AIOS/_backups",
    "D:/AIOS/__pycache__",
    "D:/AIOS/_relinked",
    "D:/AIOS/cloudtech-saas",
    "D:/AIOS/AIOS_RECONSTRUCTION",
    "D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL",
    "D:/AIOS/daemons_v2",
    "D:/AIOS/reports",
    "D:/AIOS/tools",
    "D:/AIOS/tmp",
    "D:/AIOS/wmic_forensics",
    "D:/AIOS/_canary",
    "D:/AIOS/_canary_restore",
    "D:/AIOS/_dr_v3.0_uncompressed_workspace",
    "D:/AIOS/_e_drive_dedup_workspace",
    "D:/AIOS/_out",
    "D:/AIOS/_patches",
    "D:/AIOS/_r274_install_backup",
    "D:/AIOS/_r348_model_swap_bak_20260930-092918",
    "D:/AIOS/_schtasks_bak",
    "D:/AIOS/_scripts",
    "D:/AIOS/_tools",
}

# Forbidden patterns for CC NEW files
FORBIDDEN_PATTERNS = [
    "protocol_*.md", "_protocol*.md",
    "version_*.md", "v1_*.md", "v2_*.md", "_v3_*.md",
    "planning_*.md",
    "handshake_*.md", "handoff_*.md",
    "spec_*.md",
    "roadmap_*.md", "blueprint_*.md",
    "playbook_*.md", "sop_*.md", "runbook_*.md",
    "_r*.py", "_R*.py",
    "r1*.py", "r2*.py", "r3*.py",
]


def is_in_whitelist(path: str) -> bool:
    path = path.replace("\\", "/")
    if path in WHITELIST_FILES:
        return True
    for wdir in WHITELIST_DIRS:
        if path.startswith(wdir):
            return True
    return False


def is_new_today(path: Path) -> bool:
    """mtime >= 今日 00:00"""
    try:
        return path.stat().st_mtime >= TODAY_START
    except OSError:
        return False


def matches_pattern(name: str):
    name_lower = name.lower()
    for pat in FORBIDDEN_PATTERNS:
        if fnmatch.fnmatch(name_lower, pat.lower()):
            return pat
    return None


def check_top_for_new(root_dir: Path):
    """检测指定目录下，今日新创建的 forbidden 文件"""
    findings = []
    if not root_dir.exists():
        return findings
    for entry in root_dir.iterdir():
        if not entry.is_file():
            continue
        if not is_new_today(entry):
            continue
        rel = str(entry).replace("\\", "/")
        if is_in_whitelist(rel):
            continue
        pat = matches_pattern(entry.name)
        if pat:
            findings.append((rel, pat))
    return findings


def ensure_evidence_dir():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def run_preflight(output_path: Path = None) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    today_str = date.today().isoformat()

    checks = {
        "aios_root_new_today": check_top_for_new(AIOS_ROOT),
        "aios_tasks_root_new_today": check_top_for_new(AIOS_ROOT / "aios_tasks"),
    }

    total = sum(len(v) for v in checks.values())
    status = "CLEAN" if total == 0 else "DIRTY"

    lines = [
        "# Preflight Check Report v4",
        "",
        f"**Timestamp**: {timestamp}",
        f"**Today**: {today_str}",
        f"**Status**: {status}",
        f"**Total Issues**: {total}",
        f"**Scope**: 仅查 '今日新创建 (mtime >= {today_str} 00:00) 且命中 forbidden 模式'",
        f"**Whitelist**: cards/, evidence/, kernel/, aios_tasks/, aios_tools/, aios_venv/, _archived/, _backups/, 以及静态 SSOT",
        "",
    ]

    if total == 0:
        lines.append("## Verdict")
        lines.append("**PASS** — 今日未发现 CC 创建的 forbidden 文件。开工允许。")
    else:
        for category, files in checks.items():
            lines.append(f"## {category}: {len(files)} files")
            for fpath, pat in files:
                lines.append(f"- `{fpath}` (matched: `{pat}`)")
            lines.append("")

    ensure_evidence_dir()
    if output_path is None:
        output_path = EVIDENCE_DIR / f"preflight_{timestamp}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\nReport: {output_path}")

    return 0 if total == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="输出文件路径")
    output_arg = parser.parse_args()
    output_path = Path(output_arg.output) if output_arg.output else None
    sys.exit(run_preflight(output_path))