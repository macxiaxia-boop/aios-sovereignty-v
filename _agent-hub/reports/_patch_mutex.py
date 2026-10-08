"""Add mutex check at start of consumer: if lock exists + PID alive, exit 0; if PID dead, take over lock."""
import re
from pathlib import Path

target = Path(r"D:\AIOS\_agent-hub\v2\src\start_consumer_real.py")
src = target.read_text(encoding="utf-8")

# Find the args = ... parse_args... section and inject mutex check BEFORE main loop
inject_point = "def main() -> int:"
# We want to add a check at the very top of main() that:
# 1. Reads the lock file
# 2. If lock exists + PID inside is alive → exit 0 (singleton)
# 3. If lock exists + PID dead → take over (overwrite lock)
# 4. If no lock → acquire by writing our PID, then proceed
# On exit (normal or exception), remove the lock

lock_check_code = '''
def _singleton_check() -> bool:
    """Return True if we should proceed. False if another consumer is alive."""
    import os, time
    v2_root = Path(os.environ.get("AIOS_V2_ROOT", r"D:\\AIOS\\_agent-hub\\v2")).resolve()
    lock_path = v2_root / "state" / ".aios_v2_consumer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        try:
            content = lock_path.read_text(encoding="utf-8").strip()
            m = re.search(r"PID=(\\d+)", content)
            if m:
                pid = int(m.group(1))
                import psutil
                if psutil.pid_exists(pid):
                    try:
                        p = psutil.Process(pid)
                        if "start_consumer_real" in " ".join(p.cmdline()):
                            print(f"[start_consumer_real] another consumer alive (PID {pid}); exiting 0")
                            return False
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except (OSError, ValueError):
            pass
        # Stale lock — take over
        try:
            lock_path.unlink()
        except OSError:
            pass

    # Acquire
    lock_path.write_text(f"PID={os.getpid()} TIME={time.time()}\\n", encoding="utf-8")
    print(f"[start_consumer_real] acquired singleton lock PID={os.getpid()}")
    return True


def _release_lock():
    import os
    v2_root = Path(os.environ.get("AIOS_V2_ROOT", r"D:\\AIOS\\_agent-hub\\v2")).resolve()
    lock_path = v2_root / "state" / ".aios_v2_consumer.lock"
    try:
        lock_path.unlink()
    except OSError:
        pass


import atexit
atexit.register(_release_lock)

'''

# Insert at top of file (after shebang/docstring)
new_src = lock_check_code + src

# Modify the if __name__ block to call _singleton_check first
new_src = new_src.replace(
    'if __name__ == "__main__":\n    v2_consumer.set_dispatcher(_claude_dispatch_adapter)',
    'if __name__ == "__main__":\n    if not _singleton_check():\n        sys.exit(0)\n    v2_consumer.set_dispatcher(_claude_dispatch_adapter)',
)

target.write_text(new_src, encoding="utf-8")
print(f"Mutex patch applied to {target}")
print(f"File size: {len(new_src)} bytes")

# Add psutil check
psutil_check = '''
try:
    import psutil
except ImportError:
    psutil = None
'''
if "import psutil" not in new_src:
    new_src = psutil_check + new_src
    target.write_text(new_src, encoding="utf-8")
    print("psutil stub added")