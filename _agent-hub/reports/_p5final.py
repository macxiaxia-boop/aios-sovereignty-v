import sys, json
sys.path.insert(0, r"D:\AIOS\_agent-hub\v2")
from src.envelope import build_envelope
from src import queue as q
env = build_envelope(
    sender="codex", recipient="claudecode", message_type="task",
    payload={"objective": "P5 final: write HELLO_FROM_ADAPTER to p5_real/out.txt and exit", "ts": "now", "workdir": r"D:\AIOS\_agent-hub\reports\p5_real"},
)
r = q.enqueue(env, dest="inbox")
print(env["id"])
