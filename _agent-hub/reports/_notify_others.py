"""Send Codex → 01a11935 wake-up notification via v2 inbox + create handoff notification for all consumers."""
import sys, json
sys.path.insert(0, r"D:\AIOS\_agent-hub\v2")
from src.envelope import build_envelope
from src import queue as q

# 1) Notification for 01a11935 main dispatcher (broadcast so any worker reads it)
env1 = build_envelope(
    sender="codex",
    recipient="broadcast",
    message_type="message",
    payload={
        "from": "Codex thread 01a11bca",
        "to": "Codex thread 01a11935 (main dispatcher) + any other Codex/CC thread",
        "subject": "AIOS Core Spine 施工完成 + V6.3 T03/T05 done",
        "handoff_doc": "D:\\AIOS\\_agent-hub\\handoff\\2026-10-08_CODEX_SUPERVISOR_HANDOFF.md",
        "v6_3_git_commit": "34d751482d56240af22f2d3b44ecca3560e2e38b",
        "dashboard_refreshed": "23:08",
        "v2_consumer_pid": 32236,
        "v2_state_json_exists": True,
        "scheduled_task_status": "BLOCKED (elevation denied, manual start required)",
        "actions_recommended": [
            "read handoff doc",
            "verify consumer still alive (wmic)",
            "if 01a11935 idle: resume dispatching V6.3 T04/T06/T07 or other open items",
            "do NOT trust 'PASS' reports — verify with wmic + schtasks + state.json check"
        ],
    },
)
r1 = q.enqueue(env1, dest="inbox")
print(f"broadcast notification: {env1['id']}, deduped={r1['deduped']}")

# 2) Direct envelope to 01a11935 (Codex main dispatcher)
env2 = build_envelope(
    sender="codex",
    recipient="codex",
    message_type="message",
    payload={
        "from": "01a11bca (AIOS Core Spine 施工会话)",
        "to": "01a11935 (Codex main dispatcher)",
        "wake_up": True,
        "handoff_doc": "D:\\AIOS\\_agent-hub\\handoff\\2026-10-08_CODEX_SUPERVISOR_HANDOFF.md",
        "what_done": "P0 审计 + P2 真活闭环 + P5 V7 真活闭环 + 11 真 bug 修复 + Hubble worker 真做 V6.3 T03 (10/10 PASS) + T05 (verify.yml CI)",
        "v6_3_commit": "34d751482d56240af22f2d3b44ecca3560e2e38b",
        "dashboard_updated_at": "23:08",
        "what_pending": [
            "60s 真验证 v2 consumer 持续运行",
            "P3/P4/P6/P7/P8 剩余 acceptance tests (T07-T12, T14, T16-T17, T20, T22-T24)",
            "Scheduled Task 持久化（被权限阻止，需要 elevated 终端）"
        ],
        "warning": "你之前报'没卡'但 narrative 已 idle 30 min。请现在做事后请把 Linnaeus/Confucius active → DONE 占位清理，并继续派 T04/T06/T07 或别的事。"
    },
)
r2 = q.enqueue(env2, dest="inbox")
print(f"to 01a11935: {env2['id']}, deduped={r2['deduped']}")

print(f"\nboth written to inbox. Other Codex/CC threads should see this when they next receive --agent codex")