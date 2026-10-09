"""_admin_disable_watchdogs.py - R-Codex-Cure-2026-09-29
跑在管理员上下文: 停 R313/R316 schtasks + 启用 V4 watchdog.
用 win32com + ctypes + schtasks.exe.
"""
import ctypes
import ctypes.wintypes as w
import subprocess
import sys
import os

advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

RESULT_FILE = r"D:\AIOS\_admin_disable_result.txt"


def write_result(stage: str, ok: bool, msg: str = ""):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{stage}] ok={ok} {msg}\n")
    print(f"[{stage}] ok={ok} {msg}")


def main():
    # 清空 result
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("")

    # 检查管理员
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False
    write_result("ADMIN", is_admin, f"is_admin={is_admin}")
    if not is_admin:
        write_result("FAIL", False, "不是管理员")
        return 2

    # 1. 删 R313 schtasks
    r = subprocess.run(
        ["schtasks.exe", "/Delete", "/TN", "OpenAI-Codex-Desktop-Watchdog-R313", "/F"],
        capture_output=True, text=True, encoding="gbk", errors="ignore", timeout=10,
    )
    write_result("DELETE_R313", r.returncode == 0, f"rc={r.returncode}, stdout={r.stdout.strip()[:80]}")

    # 2. 删 R316 schtasks
    r = subprocess.run(
        ["schtasks.exe", "/Delete", "/TN", "OpenAI-Codex-Beta-Watchdog-R316", "/F"],
        capture_output=True, text=True, encoding="gbk", errors="ignore", timeout=10,
    )
    write_result("DELETE_R316", r.returncode == 0, f"rc={r.returncode}, stdout={r.stdout.strip()[:80]}")

    # 3. 注册 V4 watchdog (开机启动 + 每分钟跑)
    V4_TASK = "Codex-Codex-Cure-V4-Watchdog"
    PYTHON_PATH = r"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"
    V4_SCRIPT = r"D:\AIOS\_openai_codex_beta_watchdog.py"

    # 先删（如果已存在）
    subprocess.run(
        ["schtasks.exe", "/Delete", "/TN", V4_TASK, "/F"],
        capture_output=True, text=True, encoding="gbk", errors="ignore", timeout=10,
    )

    # 创建新任务: 开机启动, 每分钟重复
    r = subprocess.run(
        [
            "schtasks.exe", "/Create",
            "/TN", V4_TASK,
            "/TR", f'"{PYTHON_PATH}" -u "{V4_SCRIPT}" 60',
            "/SC", "ONSTART",
            "/DELAY", "0000:30",
            "/RL", "HIGHEST",
            "/RU", "SYSTEM",
            "/F",
        ],
        capture_output=True, text=True, encoding="gbk", errors="ignore", timeout=10,
    )
    write_result("CREATE_V4", r.returncode == 0, f"rc={r.returncode}, stdout={r.stdout.strip()[:80]}")

    # 4. 立即跑一次 V4 watchdog (确保它在后台)
    try:
        subprocess.Popen(
            [PYTHON_PATH, "-u", V4_SCRIPT, "60"],
            creationflags=0x08000008,
        )
        write_result("START_V4", True, "后台启动 V4 watchdog")
    except Exception as e:
        write_result("START_V4", False, f"failed: {e}")

    # 5. 验证 V4 任务在
    r = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", V4_TASK],
        capture_output=True, text=True, encoding="gbk", errors="ignore", timeout=10,
    )
    write_result("QUERY_V4", r.returncode == 0, f"rc={r.returncode}, has_task_name={('TaskName' in r.stdout)}")

    write_result("DONE", True, "watchdog 配置完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())