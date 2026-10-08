"""Restore start_consumer_real.py from backup and apply clean mutex patch."""
import shutil
import re
from pathlib import Path

target = Path(r"D:\AIOS\_agent-hub\v2\src\start_consumer_real.py")

# Find latest backup
backups = sorted(Path(r"D:\AIOS\_agent-hub\reports").glob("start_consumer_real_*.bak*"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
print(f"Found {len(backups)} backups")
if backups:
    print(f"Latest: {backups[0]}")
    # Restore from .bak file
    src = backups[0].read_text(encoding="utf-8")
    target.write_text(src, encoding="utf-8")
    print(f"Restored from {backups[0].name}")

# Now apply clean patch: just add _singleton_check function + import psutil + modify main
src = target.read_text(encoding="utf-8")

# Add psutil try/import after existing imports
if "import psutil" not in src:
    src = src.replace(
        "from pathlib import Path\n",
        "from pathlib import Path\ntry:\n    import psutil\nexcept ImportError:\n    psutil = None\n",
        1
    )

# Add _singleton_check + _release_lock at end (before main) -- but main is just if __name__ block
# So just append at end
mutex_block = '''

def _singleton_check():
    """Singleton lock: return True if we should proceed, False if another consumer is alive."""
    import os, time, re as _re
    v2_root = Path(os.environ.get("AIOS_V2_ROOT", r"D:\\\\AIOS\\\\_agent-hub\\\\v2")).resolve()
    lock_path = v2_root / "state" / ".aios_v2_consumer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        try:
            content = lock_path.read_text(encoding="utf-8").strip()
            m = _re.search(r"PID=(\\d+)", content)
            if m and psutil:
                pid = int(m.group(1))
                if psutil.pid_exists(pid):
                    try:
                        p = psutil.Process(pid)
                        if "start_consumer_real" in " ".join(p.cmdline()):
                            print(f"[singleton] another consumer alive (PID {pid}); exiting")
                            return False
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except (OSError, ValueError):
            pass
        try:
            lock_path.unlink()
        except OSError:
            pass

    lock_path.write_text(f"PID={os.getpid()} TIME={time.time()}\\n", encoding="utf-8")
    print(f"[singleton] acquired PID={os.getpid()}")
    return True


def _release_lock():
    import os
    v2_root = Path(os.environ.get("AIOS_V2_ROOT", r"D:\\\\AIOS\\\\_agent-hub\\\\v2")).resolve()
    lock_path = v2_root / "state" / ".aios_v2_consumer.lock"
    try:
        lock_path.unlink()
    except OSError:
        pass


import atexit
atexit.register(_release_lock)
'''

src = src + mutex_block

# Add singleton check in main block
src = src.replace(
    'if __name__ == "__main__":\n    v2_consumer.set_dispatcher(_claude_dispatch_adapter)',
    'if __name__ == "__main__":\n    if not _singleton_check():\n        sys.exit(0)\n    v2_consumer.set_dispatcher(_claude_dispatch_adapter)',
)

target.write_text(src, encoding="utf-8")
print(f"Clean patch applied. File size: {len(src)}")

# Verify syntax
import ast
try:
    ast.parse(src)
    print("✅ syntax OK")
except SyntaxError as e:
    print(f"❌ syntax error: {e}")