"""start_ecosystem.py - 启动整个 AI 栈: AIOS + Codex + ClaudeCode.
解决 Codex + claudecode 闪退根因: AIOS daemon 没跑导致 aios-interop MCP 失败.
"""
import subprocess
import sys
import ctypes
import ctypes.wintypes as w
import time

# 路径
AIOS_DAEMON = r"D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe"
CHATGPT_EXE = r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\ChatGPT.exe"
CLAUDE_CODE = r"D:\npm-global\claude.cmd"


def kill_codex():
    """杀所有 Codex 进程"""
    subprocess.run(
        ["taskkill", "/F", "/IM", "ChatGPT.exe", "/T"],
        capture_output=True, encoding='gbk', errors='ignore',
        timeout=10, creationflags=0x08000008,
    )
    subprocess.run(
        ["taskkill", "/F", "/IM", "codex.exe", "/T"],
        capture_output=True, encoding='gbk', errors='ignore',
        timeout=10, creationflags=0x08000008,
    )
    subprocess.run(
        ["taskkill", "/F", "/IM", "codex-command-runner.exe", "/T"],
        capture_output=True, encoding='gbk', errors='ignore',
        timeout=10, creationflags=0x08000008,
    )
    subprocess.run(
        ["taskkill", "/F", "/IM", "codex-windows-sandbox-service.exe", "/T"],
        capture_output=True, encoding='gbk', errors='ignore',
        timeout=10, creationflags=0x08000008,
    )


def kill_claude():
    subprocess.run(
        ["taskkill", "/F", "/IM", "claude.exe", "/T"],
        capture_output=True, encoding='gbk', errors='ignore',
        timeout=10, creationflags=0x08000008,
    )


def is_running(name: str) -> bool:
    r = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {name}"],
        capture_output=True, text=True, encoding='gbk', errors='ignore',
        timeout=5, creationflags=0x08000008,
    )
    return name in (r.stdout or "")


def start_aios():
    print(f"\n[1/4] 启动 AIOS daemon ...")
    if is_running("AIOS_Autonomy_Daemon.exe"):
        print("  AIOS daemon 已在跑")
        return True
    p = subprocess.Popen(
        [AIOS_DAEMON],
        creationflags=0x08000008,  # CREATE_NO_WINDOW
    )
    print(f"  启动 PID={p.pid}, 等 10s ...")
    time.sleep(10)
    if is_running("AIOS_Autonomy_Daemon.exe"):
        print(f"  ✓ AIOS daemon 启动成功")
        return True
    print(f"  ✗ AIOS daemon 启动失败")
    return False


def start_codex():
    print(f"\n[2/4] 启动 Codex ...")
    if is_running("ChatGPT.exe"):
        print("  Codex 已在跑")
        return True
    p = subprocess.Popen(
        [CHATGPT_EXE],
        creationflags=0x08000008,
    )
    print(f"  启动 PID={p.pid}")
    return True


def start_claude():
    print(f"\n[3/4] 启动 ClaudeCode ...")
    if is_running("claude.exe"):
        print("  ClaudeCode 已在跑")
        return True
    if not __import__('os').path.exists(CLAUDE_CODE):
        print(f"  ClaudeCode 路径不存在: {CLAUDE_CODE}")
        return False
    p = subprocess.Popen(
        [CLAUDE_CODE],
        creationflags=0x08000008,
    )
    print(f"  启动 PID={p.pid}")
    return True


def check_after_30s():
    print(f"\n[4/4] 等 30s 后检查状态 ...")
    time.sleep(30)
    print("\n=== 30s 后 AI 栈状态 ===")
    for name in ["AIOS_Autonomy_Daemon.exe", "claude.exe", "ChatGPT.exe", "codex.exe"]:
        running = is_running(name)
        print(f"  {name}: {'✓ 在跑' if running else '✗ 不在跑'}")


def main():
    print("=== AI 栈恢复启动 ===\n")

    # 0. 先杀 Codex + Claude
    print("[0/4] 先杀 Codex + Claude ...")
    kill_codex()
    kill_claude()
    time.sleep(3)

    # 1. 启动 AIOS (最重要!)
    aios_ok = start_aios()
    if not aios_ok:
        print("\n✗ AIOS 启动失败, Codex + Claude 仍会闪退")
        return 1

    # 2-3. 启动 Codex + Claude
    start_codex()
    start_claude()

    # 4. 验证
    check_after_30s()

    print("\n=== 完成 ===")
    print("如果 Codex + Claude 30s 后还在跑, 说明闪退已根治")
    print("如果闪退仍存在, 跑下面的命令收集更多信息:")
    print("  python D:\\AIOS\\check_ai_stack.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())