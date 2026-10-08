import sys, json
sys.path.insert(0, r"D:\AIOS\_agent-hub\v2")
from src.envelope import build_envelope
from src import queue as q
env = build_envelope(
    sender="codex", recipient="claudecode", message_type="task",
    payload={"objective": "T07 final: confirm no-loop after guard", "ts": "now"},
)
r = q.enqueue(env, dest="inbox")
print(json.dumps({"id": env["id"], "file": r["file"]}))
