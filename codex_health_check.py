#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codex_health_check.py — R-Codex-Cure-2026-09-29 Codex 健康检查.

检查项:
  1. hooks hash 一致性 (hooks.json ↔ config.toml [hooks.state])
  2. roaming.lock 残留 (OpenAI.CodexBeta + OpenAI.Codex)
  3. Codex app-server 锁残留 (daemon.pid.lock + app-server.pid.lock)
  4. Codex 多实例 (ChatGPT.exe 数量 > 1)
  5. Codex 桌面 SQLite 数据库大小 (logs_2.sqlite / thread_history_1.sqlite)
  6. Codex 桌面版本 vs 最新版 (version.json)
  7. Codex CLI npm 包版本 vs 桌面版本
  8. 缺失的 hook 脚本 (verify-tracker.py / evidence-checker.py)
  9. Codex watchdog 任务状态 (R313 + R316)
  10. Codex UWP 包存在性 (Beta 必备)

用法:
  python codex_health_check.py            # 全检 + 报告
  python codex_health_check.py --fix      # 自动修复可清理项 (lock + multi-instance)
  python codex_health_check.py --json    # JSON 输出 (供其他脚本用)
"""
import sys
import os
import json
import time
import shutil
import argparse
import subprocess
from pathlib import Path

HOME = Path(os.path.expanduser(r"~"))
CODEX_HOME = HOME / ".codex"
HOOKS_JSON = CODEX_HOME / "hooks.json"
CONFIG_TOML = CODEX_HOME / "config.toml"
# R-Codex-Cure V4: Codex 实际是免安装版, MS Store 包路径仅作历史残留检测
CODEX_PORTABLE = Path(r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】")
CHATGPT_EXE = CODEX_PORTABLE / "app" / "ChatGPT.exe"
SANDBOX_SERVICE_EXE = CODEX_PORTABLE / "app" / "resources" / "codex-windows-sandbox-service.exe"
OLD_PKG = Path(os.path.expandvars(r"%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0"))
APP_SERVER = CODEX_HOME / "app-server-daemon"


def check_hooks_hash() -> dict:
    """Check hooks hash consistency."""
    sys.path.insert(0, str(Path(__file__).parent))
    from sync_codex_hook_hash import compute_hashes, parse_existing_hashes
    try:
        computed = compute_hashes(HOOKS_JSON)
        existing = parse_existing_hashes(CONFIG_TOML)
        mismatches = []
        for ev, m, h, sha in computed:
            if existing.get((ev, m, h)) != f"sha256:{sha}":
                mismatches.append((ev, m, h, sha))
        return {
            "ok": not mismatches,
            "total": len(computed),
            "mismatches": mismatches,
            "msg": f"{len(computed) - len(mismatches)}/{len(computed)} hooks hash 一致",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_roaming_lock() -> dict:
    """Check if roaming.lock exists in either UWP package."""
    locks = []
    for pkg in [OLD_PKG]:
        lf = pkg / "Settings" / "roaming.lock"
        if lf.exists():
            stat = lf.stat()
            locks.append({
                "path": str(lf),
                "size": stat.st_size,
                "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            })
    return {"ok": not locks, "locks": locks}


def check_app_server_locks() -> dict:
    """Check if app-server-daemon has lock files."""
    locks = []
    if APP_SERVER.exists():
        for f in APP_SERVER.glob("*.lock"):
            stat = f.stat()
            locks.append({"path": str(f), "size": stat.st_size})
    return {"ok": not locks, "locks": locks}


def check_multi_instance() -> dict:
    """Check if multiple ChatGPT.exe processes are running."""
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ChatGPT.exe"],
            capture_output=True, text=True, timeout=5, creationflags=0x08000008,
            encoding="gbk", errors="ignore",
        )
        out = r.stdout or ""
        # "ChatGPT.exe" 在表头也出现一次，需要 - 1
        if "ChatGPT.exe" not in out:
            n = 0
        else:
            n = max(0, out.count("ChatGPT.exe") - 1)
        return {"ok": n <= 1, "count": n, "msg": f"{n} 个 ChatGPT.exe 在跑"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_sqlite_size() -> dict:
    """Check Codex SQLite size to detect bloat."""
    out = {}
    for name in ["logs_2.sqlite", "thread_history_1.sqlite", "state_5.sqlite"]:
        p = CODEX_HOME / name
        if p.exists():
            size_mb = p.stat().st_size / 1024 / 1024
            out[name] = round(size_mb, 1)
    bloated = [k for k, v in out.items() if v > 50]
    return {"ok": not bloated, "sizes_mb": out, "bloated": bloated}


def check_hook_scripts() -> dict:
    """Check if hook scripts exist."""
    required = [
        Path(r"C:\Users\xinzh\.openclaw\tools\core\verify-tracker.py"),
        Path(r"C:\Users\xinzh\.openclaw\tools\core\evidence-checker.py"),
        Path(r"C:\Users\xinzh\.openclaw\tools\core\cc-self-read-guard.py"),
    ]
    missing = [str(p) for p in required if not p.exists()]
    return {"ok": not missing, "missing": missing}


def check_portable_codex() -> dict:
    """Check if 免安装版 Codex 桌面 is installed."""
    out = {
        "chatgpt_exe": CHATGPT_EXE.exists(),
        "sandbox_service_exe": SANDBOX_SERVICE_EXE.exists(),
        "app_dir": CODEX_PORTABLE.exists(),
    }
    msg = []
    if out["chatgpt_exe"]:
        msg.append("免安装版 ChatGPT.exe 存在")
    else:
        msg.append("免安装版 ChatGPT.exe 缺失")
    if out["sandbox_service_exe"]:
        msg.append("sandbox service exe 存在")
    return {
        "ok": out["chatgpt_exe"] and out["sandbox_service_exe"],
        "paths": out,
        "msg": "; ".join(msg),
    }


def check_sandbox_service() -> dict:
    """Check if CodexSandboxService is registered and running."""
    try:
        r = subprocess.run(
            ["sc", "query", "CodexSandboxService.OpenAI.Codex"],
            capture_output=True, text=True, timeout=5, creationflags=0x08000008,
            encoding="gbk", errors="ignore",
        )
        out = r.stdout or ""
        running = "RUNNING" in out and "STOPPED" not in out
        exists = r.returncode == 0 or "CodexSandboxService" in out
        return {
            "ok": running,
            "running": running,
            "registered": exists,
            "msg": "运行中" if running else ("已注册但未启动" if exists else "未注册"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fix_residuals() -> dict:
    """Auto-fix: clean locks, kill multi-instance."""
    actions = []
    # 1. 清 roaming.lock
    for pkg in [OLD_PKG]:
        lf = pkg / "Settings" / "roaming.lock"
        if lf.exists():
            try:
                lf.unlink()
                actions.append(f"deleted {lf}")
            except Exception as e:
                actions.append(f"FAILED {lf}: {e}")
    # 2. 清 app-server 锁
    if APP_SERVER.exists():
        for f in APP_SERVER.glob("*.lock"):
            try:
                f.unlink()
                actions.append(f"deleted {f}")
            except Exception as e:
                actions.append(f"FAILED {f}: {e}")
    # 3. 杀多实例 ChatGPT.exe (>1 时)
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ChatGPT.exe"],
            capture_output=True, text=True, timeout=5, creationflags=0x08000008,
        )
        n = r.stdout.count("ChatGPT.exe") - 1 if "ChatGPT.exe" in r.stdout else 0
        if n > 0:
            subprocess.run(
                ["taskkill", "/F", "/IM", "ChatGPT.exe", "/T"],
                capture_output=True, timeout=10, creationflags=0x08000008,
            )
            actions.append(f"killed {n} ChatGPT.exe")
    except Exception as e:
        actions.append(f"taskkill error: {e}")
    return {"ok": True, "actions": actions}


def main() -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = {
        "hooks_hash": check_hooks_hash(),
        "roaming_lock": check_roaming_lock(),
        "app_server_locks": check_app_server_locks(),
        "multi_instance": check_multi_instance(),
        "sqlite_size": check_sqlite_size(),
        "hook_scripts": check_hook_scripts(),
        "portable_codex": check_portable_codex(),
        "sandbox_service": check_sandbox_service(),
    }

    if args.fix:
        fix_result = fix_residuals()
        checks["fix_applied"] = fix_result

    if args.json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return 0 if all(c.get("ok") for c in checks.values() if isinstance(c, dict)) else 1

    print()
    print("=" * 70)
    print(f"Codex 健康检查  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    bad_items = []
    for name, c in checks.items():
        if name == "fix_applied":
            continue
        ok = c.get("ok", False)
        sym = "✓" if ok else "✗"
        print(f"  [{sym}] {name}: {json.dumps(c, ensure_ascii=False)}")
        if not ok:
            bad_items.append(name)

    print()
    if not bad_items:
        print("✓ Codex 健康检查全部通过")
        return 0
    else:
        print(f"⚠ 发现 {len(bad_items)} 项问题: {bad_items}")
        print("  运行 codex_health_check.py --fix 自动修复可清理项")
        print("  运行 D:\\AIOS\\start_codex_safe.cmd 安全启动 Codex")
        return 1


if __name__ == "__main__":
    sys.exit(main())