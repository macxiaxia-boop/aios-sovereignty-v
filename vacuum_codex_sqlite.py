#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vacuum_codex_sqlite.py — R-Codex-Cure-2026-09-29 SQLite 瘦身工具.

Codex 桌面 SQLite 文件长期不 vacuum, 会一直膨胀:
  logs_2.sqlite: 388+ MB (主要是 WAL 没回收)
  thread_history_1.sqlite: 99+ MB

VACUUM 会在新位置重建 DB, 回收空间.
必须关闭 Codex 主进程再 VACUUM (SQLite 不支持并发 VACUUM).

用法:
  python vacuum_codex_sqlite.py --check     # 看大小 + 估算可回收
  python vacuum_codex_sqlite.py --vacuum    # 真瘦身
"""
import sys
import os
import argparse
import sqlite3
from pathlib import Path

CODEX_HOME = Path(os.path.expanduser(r"~/.codex"))
TARGETS = ["logs_2.sqlite", "thread_history_1.sqlite", "state_5.sqlite",
           "goals_1.sqlite", "queue_1.sqlite", "memories_1.sqlite"]


def get_size_mb(path: Path) -> float:
    if path.exists():
        return path.stat().st_size / 1024 / 1024
    return 0.0


def check_size() -> dict:
    out = {}
    total = 0.0
    for name in TARGETS:
        p = CODEX_HOME / name
        size = get_size_mb(p)
        out[name] = round(size, 1)
        total += size
    out["_total_mb"] = round(total, 1)
    return out


def vacuum_one(name: str) -> dict:
    p = CODEX_HOME / name
    if not p.exists():
        return {"ok": False, "error": "not found"}
    size_before = p.stat().st_size
    try:
        conn = sqlite3.connect(str(p))
        # 必须先关 WAL checkpoint 才能 VACUUM
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")
        conn.close()
        size_after = p.stat().st_size
        return {
            "ok": True,
            "before_mb": round(size_before / 1024 / 1024, 1),
            "after_mb": round(size_after / 1024 / 1024, 1),
            "saved_mb": round((size_before - size_after) / 1024 / 1024, 1),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--vacuum", action="store_true")
    args = ap.parse_args()
    if not args.check and not args.vacuum:
        args.check = True

    sizes = check_size()
    print(f"\nCodex SQLite 大小 (总计 {sizes['_total_mb']} MB):")
    for name in TARGETS:
        size = sizes.get(name, 0)
        flag = " ⚠ 膨胀" if size > 50 else ""
        print(f"  {name}: {size} MB{flag}")

    if args.check:
        return 0

    if args.vacuum:
        # 检查 Codex 进程
        import subprocess
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ChatGPT.exe"],
            capture_output=True, text=True, timeout=5, creationflags=0x08000008,
        )
        out = r.stdout or ""
        n = max(0, out.count("ChatGPT.exe") - 1) if "ChatGPT.exe" in out else 0
        if n > 0:
            print(f"\n⚠ 检测到 {n} 个 ChatGPT.exe 在跑, VACUUM 可能失败")
            print("  请先跑: python codex_health_check.py --fix 或手动杀进程")
            return 2

        print("\n开始 vacuum (需要确保 Codex 已关闭)...")
        total_saved = 0.0
        for name in TARGETS:
            if sizes.get(name, 0) < 10:  # 小于 10MB 不需要 vacuum
                continue
            print(f"  vacuum {name}...", end=" ", flush=True)
            r = vacuum_one(name)
            if r.get("ok"):
                saved = r.get("saved_mb", 0)
                total_saved += saved
                print(f"OK ({r.get('before_mb')}MB -> {r.get('after_mb')}MB, 省 {saved}MB)")
            else:
                print(f"FAIL: {r.get('error')}")
        print(f"\n总节省: {round(total_saved, 1)} MB")
        return 0


if __name__ == "__main__":
    sys.exit(main())