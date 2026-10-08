# v2/tests/test_01_envelope_schema.py
# Acceptance: Schema 验证通过 (完工标准 2)
#
# R320.1: removed `import pytest` and `pytest.raises` — replaced with
# try/except ValueError so the file imports cleanly without pytest installed.
from src.envelope import build_envelope, reply_envelope, verify_envelope
from src.validation import validate_envelope


def test_envelope_required_fields_present():
    env = build_envelope("codex", "claudecode", "message", {"text": "hi"})
    ok, errs = validate_envelope(env)
    assert ok, errs
    for k in ("id", "schema_version", "message_type", "sender", "recipient",
              "timestamp", "idempotency_key", "payload"):
        assert k in env, k


def test_envelope_schema_version_is_1_0():
    env = build_envelope("a", "b", "heartbeat", {"agent_id": "a", "status": "alive"})
    assert env["schema_version"] == "1.0"


def test_envelope_idempotency_key_is_sha256_hex_64():
    env = build_envelope("x", "y", "message", {"k": 1})
    assert len(env["idempotency_key"]) == 64
    int(env["idempotency_key"], 16)


def test_envelope_idempotency_key_deterministic_for_same_payload():
    e1 = build_envelope("a", "b", "message", {"x": 1})
    e2 = build_envelope("a", "b", "message", {"x": 1})
    assert e1["idempotency_key"] == e2["idempotency_key"]
    e3 = build_envelope("a", "b", "message", {"x": 2})
    assert e1["idempotency_key"] != e3["idempotency_key"]


def test_envelope_invalid_message_type_rejected():
    raised = False
    try:
        build_envelope("a", "b", "bogus", {})
    except ValueError:
        raised = True
    assert raised, "expected ValueError for invalid message_type"


def test_verify_envelope_detects_tampered_payload():
    env = build_envelope("a", "b", "message", {"x": 1})
    env["payload"]["x"] = 999
    ok, errs = verify_envelope(env)
    assert not ok
    assert any("idempotency_key mismatch" in e for e in errs)


def test_reply_envelope_has_correlation_id():
    orig = build_envelope("codex", "claudecode", "task",
                          {"task_id": "t1", "title": "x"})
    rep = reply_envelope(orig, "claudecode", "ack", {"ack_of": orig["id"]})
    assert rep["correlation_id"] == orig["id"]
    assert rep["in_reply_to"] == orig["id"]
    assert rep["recipient"] == "codex"


def test_heartbeat_payload_minimum_fields():
    env = build_envelope("codex", "broadcast", "heartbeat",
                          {"agent_id": "codex", "status": "alive"})
    assert env["message_type"] == "heartbeat"
    assert env["payload"]["agent_id"] == "codex"