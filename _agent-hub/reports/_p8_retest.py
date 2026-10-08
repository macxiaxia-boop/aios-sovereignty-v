import sys, json
sys.path.insert(0, r"D:\AIOS\_agent-hub\v2")
from src.envelope import build_envelope
from src import queue as q

env = build_envelope(
    sender="codex",
    recipient="claudecode",
    message_type="task",
    payload={
        "objective": "P8 retest: consumer auto-drains new envelope",
        "test_id": "P8-RETEST-001",
        "instructions": ["verify this envelope is auto-claimed and dispatched by consumer"],
    },
)
res = q.enqueue(env, dest="inbox")
print(json.dumps({"envelope_id": env["id"], "result": res}, default=str))
