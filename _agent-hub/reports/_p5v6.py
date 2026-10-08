"""Send fresh task + monitor consumer + check result file"""
import sys, json, time, os
sys.path.insert(0, r"D:\AIOS\_agent-hub\v2")
from src.envelope import build_envelope
from src import queue as q

env = build_envelope(
    sender="codex", recipient="claudecode", message_type="task",
    payload={"objective": "P5 V6: write HELLO_V6 to p5_real/v6.txt and exit", "ts": "now", "workdir": r"D:\AIOS\_agent-hub\reports\p5_real"},
)
res = q.enqueue(env, dest="inbox")
print(f"sent: {env['id']}")
print(f"file: {res.get('file')}")
time.sleep(15)
print("--- 15s 后 messages 目录 ---")
import os
for fn in os.listdir(r"D:\AIOS\_agent-hub\v2\messages\inbox"):
    if env["id"] in fn or "claudecode__codex" in fn:
        print(f"  {fn}: {os.path.getsize(os.path.join(r'D:\AIOS\_agent-hub\v2\messages\inbox', fn))} bytes")
print("--- deadletter ---")
for fn in os.listdir(r"D:\AIOS\_agent-hub\v2\messages\deadletter"):
    print(f"  {fn}")