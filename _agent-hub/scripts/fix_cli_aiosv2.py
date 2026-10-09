"""fix_cli_aiosv2.py — Phase-2 引入的 broken import."""
import pathlib

# 1. Delete shim queue.py — relative imports don't work outside v2 conftest context
shim = pathlib.Path(r"D:\AIOS\_agent-hub\v2\src\queue.py")
if shim.exists():
    shim.unlink()
    print(f"deleted shim: {shim}")

# 2. Fix cli/aiosv2.py
cli = pathlib.Path(r"D:\AIOS\_agent-hub\v2\cli\aiosv2.py")
src = cli.read_text(encoding="utf-8")
old = "from src.queue import ack as q_ack, claim as q_claim, deadletter, enqueue, get_envelope_by_id, list_unclaimed"
new = "from src.message_queue import ack as q_ack, claim as q_claim, deadletter, enqueue, get_envelope_by_id, list_unclaimed"
if old in src:
    src = src.replace(old, new)
    cli.write_text(src, encoding="utf-8")
    print(f"fixed cli/aiosv2.py")
else:
    print(f"cli/aiosv2.py already fixed or different")