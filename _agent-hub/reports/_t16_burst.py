import sys, json, time
sys.path.insert(0, r"D:\AIOS\_agent-hub\v2")
from src.envelope import build_envelope
from src import queue as q
ids = []
for i in range(50):
    env = build_envelope(
        sender="codex", recipient="claudecode", message_type="task",
        payload={"objective": f"T16 burst #{i}", "ts": time.time()},
    )
    q.enqueue(env, dest="inbox")
    ids.append(env["id"])
print(json.dumps({"sent": len(ids), "first_id": ids[0], "last_id": ids[-1]}))
