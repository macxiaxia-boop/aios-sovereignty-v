"""fix_aios_v2_bridge.py — Phase F Round 1 message_queue rename 后, bridge 没跟改. 修 src.queue -> src.message_queue.

关键: bridge 是 Operator/aios_tools/_aios_v2_envelope_bridge.py, 不是 git 仓库里 (in 个人文件).
但是 MCP test 跑它, 所以必须修.
"""
import pathlib

p = pathlib.Path(r"D:\个人文件\AI\Operator\aios_tools\_aios_v2_envelope_bridge.py")
src = p.read_text(encoding="utf-8")
old = "    from src import queue as _queue   # noqa: WPS433"
new = "    from src import message_queue as _queue   # noqa: WPS433  (Phase F Round 1: queue.py -> message_queue.py)"
assert old in src, "queue import not found"
src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("bridge patched: src.queue -> src.message_queue")