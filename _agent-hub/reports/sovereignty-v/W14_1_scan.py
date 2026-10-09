#!/usr/bin/env python3
"""
W14.1 · CloudTech read-only contamination scan
- 用 ACCEPTED ContaminationScanner 扫 D:\\CloudTech-Portable
- 只读 · 不改任何文件
- 输出 reports/sovereignty-v/W14_scan.json + summary stdout
"""
import sys, os, json, time
from pathlib import Path

sys.path.insert(0, r"D:\AIOS\_agent-hub\policy")
from contamination_scanner import ContaminationScanner

import yaml
POLICY_PATH = r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml"
SCAN_ROOT = r"D:\CloudTech-Portable"
OUTPUT_PATH = r"D:\AIOS\_agent-hub\reports\sovereignty-v\W14_scan.json"

EXCLUDE_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "node_modules", ".cache",
    ".uv-cache", "uv-cache", ".tox", ".eggs", "dist", "build",
    ".next", ".nuxt", ".output", "coverage", ".nyc_output",
    "_backups", "_debug_archive", "_handoffs", ".pytest_cache",
    "backups", "node_modules", "dist", "build",
    ".github",
}
INCLUDE_EXTS = {".py", ".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx",
               ".yaml", ".yml", ".json"}
MAX_FILE_SIZE = 500_000
MAX_FILES = 3000

def main():
    print(f"=== W14.1 CloudTech read-only scan ===")
    print(f"scan_root: {SCAN_ROOT}")
    print(f"exclude_dirs: {len(EXCLUDE_DIRS)} patterns")
    print(f"max_files: {MAX_FILES}  max_size: {MAX_FILE_SIZE:,d} bytes")
    print()

    t0 = time.time()
    policy = yaml.safe_load(open(POLICY_PATH, encoding="utf-8").read())
    scanner = ContaminationScanner(policy=policy, max_content_bytes=MAX_FILE_SIZE)

    stats = {
        "files_scanned": 0,
        "files_skipped_excluded": 0,
        "files_skipped_too_big": 0,
        "files_skipped_extension": 0,
        "files_with_findings": 0,
        "total_findings": 0,
        "by_classification": {},
        "findings_by_keyword": {},
    }
    all_findings = []

    scan_root = Path(SCAN_ROOT)
    if not scan_root.exists():
        print(f"ERROR: {scan_root} not found")
        return

    for p in scan_root.rglob("*"):
        if stats["files_scanned"] >= MAX_FILES:
            print(f"  [MAX FILES REACHED] stop at {MAX_FILES}")
            break
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            stats["files_skipped_excluded"] += 1
            continue
        if p.suffix.lower() not in INCLUDE_EXTS:
            stats["files_skipped_extension"] += 1
            continue
        try:
            if p.stat().st_size > MAX_FILE_SIZE:
                stats["files_skipped_too_big"] += 1
                continue
        except OSError:
            continue

        stats["files_scanned"] += 1
        try:
            findings = scanner.scan_path(str(p))
        except Exception as e:
            findings = []
        if findings:
            stats["files_with_findings"] += 1
            for f in findings:
                stats["total_findings"] += 1
                cls = f.classification.value if hasattr(f, "classification") else "UNKNOWN"
                stats["by_classification"][cls] = stats["by_classification"].get(cls, 0) + 1
                kw = getattr(f, "keyword", getattr(f, "match", "?"))
                stats["findings_by_keyword"][kw] = stats["findings_by_keyword"].get(kw, 0) + 1
                all_findings.append({
                    "classification": cls,
                    "path": str(p),
                    "line": getattr(f, "line", 0),
                    "keyword": kw,
                    "severity": getattr(f, "severity", "?"),
                    "rationale": getattr(f, "rationale", ""),
                    "evidence": getattr(f, "evidence", "")[:300] if getattr(f, "evidence", "") else "",
                })
        if stats["files_scanned"] % 100 == 0:
            print(f"  scanned {stats['files_scanned']} ... findings={stats['total_findings']}")

    elapsed = time.time() - t0

    print()
    print(f"=== W14.1 SCAN COMPLETE ===")
    print(f"elapsed: {elapsed:.1f}s")
    print(f"files_scanned: {stats['files_scanned']}")
    print(f"files_with_findings: {stats['files_with_findings']}")
    print(f"total_findings: {stats['total_findings']}")
    print(f"by_classification: {stats['by_classification']}")
    print(f"top_keywords: {sorted(stats['findings_by_keyword'].items(), key=lambda x: -x[1])[:10]}")

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    report = {
        "phase": "W14.1",
        "scan_root": SCAN_ROOT,
        "ts": time.time(),
        "elapsed_seconds": elapsed,
        "policy_id": policy.get("policy_id"),
        "policy_version": policy.get("policy_version"),
        "stats": stats,
        "findings": all_findings,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()