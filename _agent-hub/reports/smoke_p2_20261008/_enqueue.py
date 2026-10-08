import sys, json, os
# 把 v2 顶层加进 path，让 src 作为包
sys.path.insert(0, r"D:\AIOS\_agent-hub\v2")
os.environ.setdefault("AIOS_V2_ROOT", r"D:\AIOS\_agent-hub\v2")

from src.envelope import build_envelope
from src import queue as q

env = build_envelope(
    sender="codex",
    recipient="claudecode",
    message_type="task",
    payload={
        "objective": "P2 smoke: prove Codex->CC->Codex model-session round-trip via v2 inbox + claude -p",
        "test_id": "P2-SMOKE-001",
        "instructions": [
            "1. Confirm you received this envelope: python D:\\AIOS\\_agent-hub\\v2\\cli\\aiosv2.py status",
            "2. Find this envelope in v2/inbox (claudecode has 10+ existing — yours is newest)",
            "3. Write a 1-line evidence file to D:\\AIOS\\_agent-hub\\reports\\smoke_p2_20261008\\cc_evidence.txt with format: CC_OK <pid> <utc-iso8601>",
            "4. Send a result envelope back to codex via: python D:\\AIOS\\_agent-hub\\v2\\cli\\aiosv2.py send --from claudecode --to codex --type result --payload <result_json> --correlation-id <ENV_ID> --in-reply-to <ENV_ID>",
            "5. Ack this task envelope via: python D:\\AIOS\\_agent-hub\\v2\\cli\\aiosv2.py ack <ENV_ID> --actor claudecode --note 'executed'",
            "6. Return a 1-2 line final report (PID, exit code, time)"
        ],
        "forbidden": "Do NOT modify any file outside D:\\AIOS\\_agent-hub\\reports\\smoke_p2_20261008\\ and the v2 inbox/outbox."
    },
)
res = q.enqueue(env, dest="inbox")
print(json.dumps({
    "envelope_id": env["id"],
    "correlation_id": env["id"],
    "idempotency_key": env["idempotency_key"],
    "enqueue_result": res,
    "ts": env["timestamp"],
}, default=str))
