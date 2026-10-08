import sys, json, time
sys.path.insert(0, r"D:\AIOS\_agent-hub\v2")
from src.envelope import build_envelope
from src import queue as q
env = build_envelope(
    sender="codex", recipient="claudecode", message_type="task",
    payload={"objective": "T07+T12 final verify", "ts": time.time()},
)
r = q.enqueue(env, dest="inbox")
print(env["id"])
