# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# _openai_codex_beta_watchdog.py - R-Codex-Cure-2026-09-29 V4
# 监控免安装版 ChatGPT.exe (Codex 桌面) alive + 残留清理 + sandbox 服务保活
#
# V4 重大变更 (相对 V3):
#   - 监控目标: 免安装版 ChatGPT.exe (不再用 Microsoft Store Beta AUMID)
#   - 增加 CodexSandboxService 检测 + 自动启动 (避免 sandbox 服务死了 Codex 卡死)
#   - 路径常量全部指向 D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\
#
# 用法:
#   python _openai_codex_beta_watchdog.py [interval_sec]
#   默认 interval=60s
import subprocess
import time
import sys
import os
import shutil
from pathlib import Path

# ---- 路径常量 (R-Codex-Cure 2026-09-29 V4: 免安装版路径) ----
CODEX_PORTABLE = Path(r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】")
CHATGPT_EXE = CODEX_PORTABLE / "app" / "ChatGPT.exe"
SANDBOX_SERVICE_EXE = CODEX_PORTABLE / "app" / "resources" / "codex-windows-sandbox-service.exe"
SANDBOX_SETUP_EXE = CODEX_PORTABLE / "app" / "resources" / "codex-windows-sandbox-setup.exe"
SERVICE_NAME = "CodexSandboxService.OpenAI.Codex"

# 历史残留路径 (旧版 MS Store Codex)
OLD_PKG = Path(os.path.expandvars(r"%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0"))
OLD_LOCK_FILE = OLD_PKG / "Settings" / "roaming.lock"

# app-server 锁
APP_SERVER_LOCKS = [
    Path(os.path.expanduser(r"~/.codex/app-server-daemon/daemon.pid.lock")),
    Path(os.path.expanduser(r"~/.codex/app-server-daemon/app-server.pid.lock")),
    Path(os.path.expanduser(r"~/.codex/app-server-daemon/daemon.lock")),
]

LOG = Path(r"D:\AIOS\_openai_codex_beta_watchdog.log")
SYNC_HASH_SCRIPT = Path(r"D:\AIOS\sync_codex_hook_hash.py")


def run_hidden(cmd, timeout=10):
    """Run subprocess with hidden console + GBK encoding."""
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, creationflags=0x08000008,
            encoding="gbk", errors="ignore",
        )
    except Exception as e:
        return type("SimpleR", (), {"returncode": 0, "stdout": "", "stderr": str(e)})()


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def cleanup_residuals() -> list:
    """清所有残留 lock. 返回清理项列表."""
    cleared = []
    for lf in [OLD_LOCK_FILE, *APP_SERVER_LOCKS]:
        try:
            if lf.exists():
                lf.unlink()
                cleared.append(str(lf))
        except Exception as e:
            log(f"cleanup lock fail {lf}: {e}")
    return cleared


def kill_multi_instance() -> int:
    """杀极端多实例 (超过 10 个 ChatGPT.exe)."""
    r = run_hidden(["tasklist", "/FI", "IMAGENAME eq ChatGPT.exe"])
    out = r.stdout or ""
    n = max(0, out.count("ChatGPT.exe") - 1) if "ChatGPT.exe" in out else 0
    # 桌面 app 正常运行时 1-10 个进程 (main + renderer + gpu + utility)
    # 超过 10 是 watchdog 反复拉起的极端情况, 才杀
    if n > 10:
        log(f"extreme multi-instance detected: {n} ChatGPT.exe, killing all")
        run_hidden(["taskkill", "/F", "/IM", "ChatGPT.exe", "/T"])
        time.sleep(2)
        return n
    return 0


def is_chatgpt_running() -> bool:
    """Check if ChatGPT.exe (主进程) is running."""
    r = run_hidden(["tasklist", "/FI", "IMAGENAME eq ChatGPT.exe"])
    out = r.stdout or ""
    n = max(0, out.count("ChatGPT.exe") - 1) if "ChatGPT.exe" in out else 0
    return n >= 1


def is_sandbox_service_running() -> bool:
    """Check if CodexSandboxService is running."""
    r = run_hidden(["sc", "query", SERVICE_NAME])
    out = r.stdout or ""
    return "RUNNING" in out and "STOPPED" not in out


def start_sandbox_service() -> bool:
    """Start CodexSandboxService. If not registered, try to register first."""
    if not SANDBOX_SERVICE_EXE.exists():
        log(f"WARN: sandbox service exe not found: {SANDBOX_SERVICE_EXE}")
        return False
    # 先尝试启动
    r = run_hidden(["sc", "start", SERVICE_NAME])
    if r.returncode == 0:
        log("CodexSandboxService started")
        return True
    # 启动失败 → 尝试注册 (需要管理员)
    log("sandbox service not registered, attempting register")
    if SANDBOX_SETUP_EXE.exists():
        run_hidden([str(SANDBOX_SETUP_EXE), "/install"])
        time.sleep(2)
        r = run_hidden(["sc", "start", SERVICE_NAME])
        if r.returncode == 0:
            log("CodexSandboxService registered and started")
            return True
    # 备用: sc create
    log("attempting sc create CodexSandboxService")
    run_hidden(["sc", "create", SERVICE_NAME,
                f"binPath= \"{SANDBOX_SERVICE_EXE}\"",
                "start=", "auto",
                "displayname=", "Codex Sandbox Service"])
    time.sleep(2)
    r = run_hidden(["sc", "start", SERVICE_NAME])
    return r.returncode == 0


def verify_hook_hash() -> bool:
    """Run sync_codex_hook_hash.py --check."""
    if not SYNC_HASH_SCRIPT.exists():
        return True
    r = run_hidden(["python.exe", str(SYNC_HASH_SCRIPT), "--check"], timeout=15)
    return r.returncode == 0


def auto_fix_hook_hash() -> bool:
    """Try to auto-sync hooks hash."""
    if not SYNC_HASH_SCRIPT.exists():
        return False
    log("hooks hash 不一致, 自动同步 ...")
    r = run_hidden(["python.exe", str(SYNC_HASH_SCRIPT), "--sync"], timeout=15)
    return r.returncode == 0


def start_chatgpt() -> bool:
    """清残留 + 校验 hash + 启动 ChatGPT.exe."""
    cleared = cleanup_residuals()
    if cleared:
        log(f"cleared: {cleared}")
    if not verify_hook_hash():
        if not auto_fix_hook_hash():
            log("WARN: hooks hash auto-fix failed")
    # 先确保 sandbox 服务在跑
    if not is_sandbox_service_running():
        log("sandbox service not running, starting ...")
        if not start_sandbox_service():
            log("WARN: failed to start sandbox service, ChatGPT.exe may 卡死")
    # 启动 ChatGPT.exe
    log(f"starting ChatGPT.exe: {CHATGPT_EXE}")
    try:
        subprocess.Popen(
            [str(CHATGPT_EXE)],
            creationflags=0x08000008,
        )
        log("ChatGPT.exe started")
        return True
    except Exception as e:
        log(f"start failed: {e}; please start manually from 运行Codex.bat")
        return False


def main() -> int:
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    log(f"R-Codex-Cure-2026-09-29 V4 watchdog started (interval={interval}s, target=免安装版 ChatGPT.exe)")
    # 启动时立即清残留 + 检查服务
    cleanup_residuals()
    if not is_sandbox_service_running():
        log("WARN: CodexSandboxService not running at startup")
    if not verify_hook_hash():
        log("WARN: hooks hash 不一致 (启动后 Codex 会弹未授权 hook)")
    while True:
        if not is_chatgpt_running():
            log("ChatGPT.exe NOT FOUND")
            start_chatgpt()
            time.sleep(90)
        else:
            # 同时检查 sandbox 服务
            if not is_sandbox_service_running():
                log("WARN: CodexSandboxService stopped, restarting ...")
                start_sandbox_service()
            log("ChatGPT.exe OK")
        time.sleep(interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("watchdog interrupted, exit")
        sys.exit(0)