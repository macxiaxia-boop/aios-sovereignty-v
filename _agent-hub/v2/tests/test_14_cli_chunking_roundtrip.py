# v2/tests/test_14_cli_chunking_roundtrip.py
#
# R286.A: aiosv2.py CLI extensions
#
# Acceptance:
#   - `send --chunk-size N` splits payload.text into N-byte chunks
#   - chunked CLI output reports chunk_count and per-chunk dedup status
#   - non-text payloads are NOT chunked
#   - send without --chunk-size sends a single envelope (backward compat)
#   - cmd_send propagates --correlation-id and --in-reply-to (existing R320.6 behavior)
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Use a sandboxed AIOS_V2_ROOT for CLI subprocesses
import tempfile
TEST_ROOT = Path(tempfile.mkdtemp(prefix="aiosv2_cli_chunk_")).resolve()
os.environ["AIOS_V2_ROOT"] = str(TEST_ROOT)
from src.paths import ensure_dirs  # noqa: E402
ensure_dirs()

CLI = ROOT / "cli" / "aiosv2.py"


def _run_cli(*args):
    env = dict(os.environ)
    env["AIOS_V2_ROOT"] = str(TEST_ROOT)
    r = subprocess.run([sys.executable, str(CLI), *args], capture_output=True,
                       text=True, env=env, timeout=30)
    return r


def test_cli_send_default_no_chunking():
    r = _run_cli("send", "--from", "a", "--to", "b", "--type", "message",
                 "--payload", '{"text": "small"}')
    assert r.returncode == 0, f"cli failed: {r.stderr}"
    j = json.loads(r.stdout)
    assert j["ok"] is True
    assert "chunked" not in j, f"unrequested chunking should not appear; got {j!r}"
    assert j["envelope_id"]


def test_cli_send_chunk_size_triggers_chunking():
    """Use a payload small enough to fit Windows cmd line (8191 char limit on
    legacy cmd.exe; modern Windows ~32k but subprocess passes the entire argv
    to CreateProcess with a 32k limit), but larger than chunk-size."""
    # 1024-byte payload with 256-byte chunks → triggers 4 chunks.
    big = "z" * 1024
    payload = json.dumps({"text": big})
    r = _run_cli("send", "--from", "a", "--to", "b", "--type", "message",
                 "--payload", payload, "--chunk-size", "256")
    assert r.returncode == 0, f"cli failed: {r.stderr}"
    j = json.loads(r.stdout)
    assert j["ok"] is True
    assert j["chunked"] is True
    assert j["chunk_size"] == 256
    assert j["chunk_count"] == 4, f"expected 4 chunks for 1024-byte / 256-byte; got {j['chunk_count']}"
    assert len(j["chunks"]) == j["chunk_count"]
    # All chunks should be fresh (no dedup)
    assert all(not c["deduped"] for c in j["chunks"]), "fresh chunks must not be deduped"


def test_cli_send_chunk_size_no_text_payload_no_chunking():
    r = _run_cli("send", "--from", "a", "--to", "b", "--type", "message",
                 "--payload", '{"k": "no text"}', "--chunk-size", "1024")
    assert r.returncode == 0, f"cli failed: {r.stderr}"
    j = json.loads(r.stdout)
    assert j["ok"] is True
    assert "chunked" not in j, f"no text → no chunking expected; got {j!r}"


def test_cli_send_correlation_id_propagates():
    import uuid as _uuid
    cid = str(_uuid.uuid4())
    r = _run_cli("send", "--from", "a", "--to", "b", "--type", "result",
                 "--payload", '{"out": 1}', "--correlation-id", cid)
    assert r.returncode == 0, f"cli failed: {r.stderr}"
    j = json.loads(r.stdout)
    assert j["ok"] is True
    assert j["correlation_id"] == cid


def test_cli_status_returns_valid_shape():
    r = _run_cli("status")
    assert r.returncode == 0, f"cli failed: {r.stderr}"
    j = json.loads(r.stdout)
    assert "v2_root" in j
    assert "tasks_total" in j
    assert "tasks_by_state" in j
    assert "inbox_count" in j
    assert "outbox_count" in j
    assert "deadletter_count" in j


def test_cli_init_creates_state_file():
    """cmd_init must create state.json and write INIT_OK.txt."""
    # Remove state.json first
    state = TEST_ROOT / "state" / "state.json"
    if state.exists():
        state.unlink()
    r = _run_cli("init")
    assert r.returncode == 0, f"cli init failed: {r.stderr}"
    assert state.exists(), f"state.json must exist after init; got {state!r}"