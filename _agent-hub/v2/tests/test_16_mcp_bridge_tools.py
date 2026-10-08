# v2/tests/test_16_mcp_bridge_tools.py
#
# R286.A Stage 2: invoke the operator aios_interop_mcp.py bridge tools
# (task_submit, task_transition, etc.) end-to-end via the `python ... --invoke`
# path.  Tests run in an isolated AIOS_V2_ROOT so they don't touch the
# production v2 queue.  All subprocesses are mocked via env injection —
# no live codex / claude / openclaw invocation.
#
# Acceptance:
#   - task_submit creates a v2 task and returns task_id
#   - task_transition advances state machine
#   - task_heartbeat refreshes lease
#   - task_cancel transitions to cancelled
#   - envelope_send validates + enqueues a v2 envelope
#   - envelope_receive lists unclaimed envelopes for a recipient
#   - envelope_send with invalid envelope returns INVALID_ENVELOPE error
#   - text-only legacy MCP calls (codex_query with prompt only) keep working
#     (we don't actually exec codex here; we just verify the input schema +
# that the tool registration allows prompt-only args).
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Isolate AIOS_V2_ROOT so the bridge uses a temp v2 root
TEST_ROOT = Path(tempfile.mkdtemp(prefix="aiosv2_mcp_test_")).resolve()
os.environ["AIOS_V2_ROOT"] = str(TEST_ROOT)

# Make sure the v2 src/ is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))  # so _agent-hub is on path
from src.paths import ensure_dirs  # noqa: E402
ensure_dirs()

OPERATOR_TOOLS = Path(r"D:\个人文件\AI\Operator\aios_tools")
MCP_PY = OPERATOR_TOOLS / "aios_interop_mcp.py"

# R286 test auth: principal=tester, authorities=P, host=claude, secret=test_secret
# Computes the HMAC signature expected by aios_interop_mcp.py::_principal().
TEST_PRINCIPAL = "r286_tester"
TEST_AUTHORITIES = "P"
TEST_HOST = "claude"
TEST_SECRET = "r286_test_secret_do_not_use_in_prod"
import hashlib as _hashlib
import hmac as _hmac
def _compute_sig(name, auths, host, secret):
    signed = f"{name}\n{','.join(sorted(set(auths.split(','))))}\n{host}".encode("utf-8")
    return _hmac.new(secret.encode("utf-8"), signed, _hashlib.sha256).hexdigest()

_TEST_SIG = _compute_sig(TEST_PRINCIPAL, TEST_AUTHORITIES, TEST_HOST, TEST_SECRET)


def _invoke_mcp(name, args):
    """Invoke a tool via the MCP --invoke CLI path."""
    args_json = json.dumps(args)
    env = {
        **os.environ,
        "AIOS_V2_ROOT": str(TEST_ROOT),
        # Force 'claude' host so v2 strict tools are allowed
        "AIOS_MCP_HOST": TEST_HOST,
        # Inject test auth so the bridge accepts the call
        "AIOS_MCP_PRINCIPAL": TEST_PRINCIPAL,
        "AIOS_MCP_AUTHORITIES": TEST_AUTHORITIES,
        "AIOS_MCP_AUTH_SECRET": TEST_SECRET,
        "AIOS_MCP_AUTH_SIGNATURE": _TEST_SIG,
    }
    r = subprocess.run(
        [sys.executable, str(MCP_PY), "--invoke", name, args_json],
        capture_output=True, text=True, env=env,
        timeout=30,
    )
    if r.returncode not in (0, 1):
        raise AssertionError(f"--invoke {name} crashed: rc={r.returncode} stderr={r.stderr!r}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"--invoke {name} returned non-JSON: {r.stdout!r} stderr={r.stderr!r}") from e


def test_task_submit_returns_task_id_and_state_queued():
    result = _invoke_mcp("task_submit", {
        "title": "r286-mcp-submit",
        "assignee": "codex",
        "owner": "claude",
        "description": "submitted via mcp bridge",
        "timeout_ms": 30000,
        "max_retries": 2,
        "input_payload": {"k": "v"},
    })
    assert result.get("ok") is True, f"task_submit failed: {result!r}"
    assert result["state"] == "queued"
    assert "task_id" in result and len(result["task_id"]) == 36  # uuid4
    task_id = result["task_id"]

    # Cleanup: cancel the task so the test process doesn't leak it
    cancel_result = _invoke_mcp("task_cancel", {"task_id": task_id})
    assert cancel_result.get("ok") is True


def test_task_full_lifecycle_via_mcp():
    sub = _invoke_mcp("task_submit", {
        "title": "r286-mcp-lifecycle",
        "assignee": "codex",
        "owner": "claude",
        "timeout_ms": 30000,
    })
    assert sub.get("ok") is True
    tid = sub["task_id"]

    # running
    tr = _invoke_mcp("task_transition", {
        "task_id": tid, "to_state": "running", "note": "starting"
    })
    assert tr.get("ok") is True
    assert tr["state"] == "running"

    # heartbeat
    hb = _invoke_mcp("task_heartbeat", {"task_id": tid})
    assert hb.get("ok") is True
    assert hb["state"] == "running"
    assert hb["heartbeat_at"] is not None

    # succeeded with output_payload
    done = _invoke_mcp("task_transition", {
        "task_id": tid, "to_state": "succeeded",
        "output_payload": {"answer": "42"},
        "note": "done",
    })
    assert done.get("ok") is True
    assert done["state"] == "succeeded"
    assert done["output_payload"]["answer"] == "42"


def test_task_transition_invalid_state_rejected():
    sub = _invoke_mcp("task_submit", {
        "title": "r286-mcp-bad-state",
        "assignee": "codex", "owner": "claude",
    })
    tid = sub["task_id"]
    # Try invalid transition: queued → succeeded (not allowed)
    bad = _invoke_mcp("task_transition", {
        "task_id": tid, "to_state": "succeeded",
    })
    assert bad.get("ok") is False, f"expected failure for bad transition; got {bad!r}"
    # Cleanup
    _invoke_mcp("task_cancel", {"task_id": tid})


def test_task_heartbeat_on_non_running_task_rejected():
    """Heartbeat requires task state == 'running'."""
    sub = _invoke_mcp("task_submit", {
        "title": "r286-mcp-hb-queued",
        "assignee": "codex", "owner": "claude",
    })
    tid = sub["task_id"]
    hb = _invoke_mcp("task_heartbeat", {"task_id": tid})
    assert hb.get("ok") is False, f"heartbeat on queued must fail; got {hb!r}"
    _invoke_mcp("task_cancel", {"task_id": tid})


def test_envelope_send_and_receive_roundtrip_via_mcp():
    """Send an envelope via MCP, then receive it back."""
    import uuid as _uuid
    eid = str(_uuid.uuid4())
    from src.envelope import build_envelope
    from src.id import utc_now_iso, idempotency_key
    # Build a valid v2 envelope
    sender = "claude"
    recipient = "codex"
    msg_type = "message"
    payload = {"text": "r286-mcp-roundtrip", "__r286_test__": "test_mcp_roundtrip"}
    env = {
        "id": eid,
        "schema_version": "1.0",
        "message_type": msg_type,
        "sender": sender,
        "recipient": recipient,
        "timestamp": utc_now_iso(),
        "idempotency_key": idempotency_key(sender, recipient, msg_type, payload),
        "payload": payload,
    }
    send = _invoke_mcp("envelope_send", {"envelope": env})
    assert send.get("ok") is True, f"envelope_send failed: {send!r}"
    assert send["envelope_id"] == eid
    assert send["deduped"] is False

    # Receive it back (recipient=codex, no claim)
    recv = _invoke_mcp("envelope_receive", {"recipient": "codex", "limit": 100, "claim": False})
    assert recv.get("ok") is True
    items = recv["items"]
    # Find our envelope
    found = [it for it in items if it["envelope_id"] == eid]
    assert len(found) == 1, f"expected to receive our envelope; got items={[i['envelope_id'] for i in items]}"
    assert found[0]["sender"] == "claude"
    assert found[0]["message_type"] == "message"


def test_envelope_send_invalid_envelope_returns_error():
    """envelope_send MUST reject envelopes missing required fields."""
    bad = _invoke_mcp("envelope_send", {"envelope": {"k": "no_required_fields"}})
    assert bad.get("ok") is False
    assert bad.get("error", {}).get("code") == "INVALID_ENVELOPE", (
        f"expected INVALID_ENVELOPE error code; got {bad!r}"
    )


def test_envelope_send_wrong_schema_version_rejected():
    bad = _invoke_mcp("envelope_send", {"envelope": {
        "id": "11111111-1111-4111-8111-111111111111",
        "schema_version": "2.0",  # wrong
        "message_type": "message",
        "sender": "a", "recipient": "b",
        "timestamp": "2026-09-30T00:00:00Z",
        "idempotency_key": "0" * 64,
        "payload": {},
    }})
    assert bad.get("ok") is False, f"expected rejection of schema_version=2.0; got {bad!r}"


def test_task_submit_validates_required_fields():
    """task_submit without title must fail with INVALID_ARGUMENT."""
    bad = _invoke_mcp("task_submit", {"assignee": "codex", "owner": "claude"})
    assert bad.get("ok") is False
    assert bad.get("error", {}).get("code") == "INVALID_ARGUMENT", (
        f"expected INVALID_ARGUMENT; got {bad!r}"
    )


def test_task_submit_validates_timeout_bounds():
    bad = _invoke_mcp("task_submit", {
        "title": "x", "assignee": "codex", "owner": "claude",
        "timeout_ms": 10,  # below 1000 minimum
    })
    assert bad.get("ok") is False
    assert bad.get("error", {}).get("code") == "INVALID_ARGUMENT"