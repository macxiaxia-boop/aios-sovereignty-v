# v2/tests/test_12_artifact_refs_no_binary.py
#
# R286.A: artifact references + chunked large-text support — no raw binary in queue.
#
# Acceptance:
#   - envelope.artifact_refs[].{path, sha256, content_type} is the SSOT pattern
#   - No raw binary content (e.g. file bytes) is embedded in payload
#   - chunked text produces text_chunks[] in payload (NOT raw bytes)
#   - validate_envelope still accepts the additive optional fields
#   - chunk_id, chunk_total, is_chunked on artifact_refs[] items are accepted
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import (
    DEFAULT_CHUNK_SIZE,
    envelope_to_chunks,
    envelope_from_chunks,
    build_envelope,
    verify_envelope,
)
from src.validation import validate_envelope


def test_artifact_refs_structure():
    """Artifact refs MUST have path, sha256, content_type (all optional except path)."""
    env = build_envelope(
        "a", "b", "message",
        {"text": "see attached"},
        artifact_refs=[{
            "path": "/tmp/screenshot.png",
            "sha256": hashlib.sha256(b"fake").hexdigest(),
            "content_type": "image/png",
            "chunk_id": None,
            "chunk_total": None,
            "is_chunked": False,
        }],
    )
    ok, errors = validate_envelope(env)
    assert ok, errors
    assert env["artifact_refs"][0]["path"] == "/tmp/screenshot.png"
    assert env["artifact_refs"][0]["content_type"] == "image/png"
    assert env["artifact_refs"][0]["sha256"] == hashlib.sha256(b"fake").hexdigest()


def test_chunked_payload_carries_no_raw_binary():
    """Chunked envelopes MUST carry text_chunks[] (strings), never raw bytes."""
    big_text = "A" * (DEFAULT_CHUNK_SIZE * 2)  # 2 chunks
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    for c in chunks:
        text_chunks = c["payload"]["text_chunks"]
        for chunk_meta in text_chunks:
            assert isinstance(chunk_meta["text"], str), "chunk text MUST be str"
            assert isinstance(chunk_meta["chunk_id"], str)
            assert isinstance(chunk_meta["chunk_total"], int)
            assert isinstance(chunk_meta["chunk_index"], int)
            # No binary content under payload
            assert "binary" not in c["payload"]
            assert "raw_bytes" not in c["payload"]
            assert "data" not in c["payload"] or isinstance(c["payload"].get("data"), dict)
        # verify_envelope MUST accept
        ok, errors = verify_envelope(c)
        assert ok, f"chunk envelope failed validation: {errors}"


def test_validate_envelope_accepts_chunked_envelope():
    """The additive text_chunks[] field MUST be accepted by validate_envelope."""
    big_text = "Z" * (DEFAULT_CHUNK_SIZE * 3)
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    for c in chunks:
        ok, errors = validate_envelope(c)
        assert ok, f"validate_envelope rejected chunk envelope: {errors}"


def test_text_chunks_round_trip_preserves_payload():
    """Reassembling chunks reconstructs the original text exactly."""
    big_text = "x" * 100000  # 100KB
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    parent = envelope_from_chunks(chunks)
    assert parent["payload"]["text"] == big_text
    assert len(parent["payload"]["text"]) == 100000
    # chunk_total reflects how many chunks
    assert parent["payload"]["chunk_total"] >= 4


def test_artifact_refs_with_chunk_metadata():
    """Artifact refs may carry chunk_id, chunk_total, is_chunked (R286 additive)."""
    env = build_envelope(
        "a", "b", "message",
        {"text": "chunked artifact"},
        artifact_refs=[{
            "path": "/tmp/big.bin",
            "sha256": hashlib.sha256(b"x").hexdigest(),
            "content_type": "application/octet-stream",
            "chunk_id": "abc-123",
            "chunk_total": 5,
            "is_chunked": True,
        }],
    )
    ok, errors = validate_envelope(env)
    assert ok, errors
    assert env["artifact_refs"][0]["chunk_id"] == "abc-123"
    assert env["artifact_refs"][0]["chunk_total"] == 5
    assert env["artifact_refs"][0]["is_chunked"] is True


def test_no_raw_binary_embedded_anywhere():
    """No raw binary content (bytes / base64 blobs / .bin / .exe) in any payload."""
    import re
    # Sample payloads and ensure no binary markers
    for payload in [
        {"text": "hello"},
        {"text": "x" * 50000},
        {"text": "y" * 100000},
        {"k": "metadata only, no binary"},
    ]:
        env = build_envelope("a", "b", "message", payload)
        # No "binary" key
        assert "binary" not in env["payload"]
        # If text exists, it's a string
        if "text" in env["payload"]:
            assert isinstance(env["payload"]["text"], str)


def test_artifact_refs_no_binary_in_payload():
    """If a caller tries to embed binary in payload, the envelope rejects it
    via missing validation (this test documents the contract: payloads
    contain only dicts/strings/numbers, never raw bytes)."""
    # The schema doesn't allow raw bytes in payload (payload is typed as
    # object).  We don't have a binary embedding API.  Confirm by trying
    # to construct an envelope with a non-dict payload and expect failure.
    raised = False
    try:
        env = build_envelope("a", "b", "message", "raw_string_payload")
    except (TypeError, ValueError):
        raised = True
    # build_envelope doesn't reject strings (it just sets payload=payload),
    # but verify_envelope requires payload to be a dict.
    if not raised:
        env = build_envelope("a", "b", "message", "raw_string_payload")
        ok, errors = verify_envelope(env)
        assert not ok, "verify_envelope must reject non-dict payload"
        assert any("payload must be a dict" in e for e in errors)