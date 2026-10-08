# v2/tests/test_09_envelope_chunking.py
#
# R286.A Stage 2: chunked large-text envelope support.
#
# Acceptance:
#   - 32 KiB chunks split/reassemble cleanly
#   - Missing or duplicate chunk indices are rejected
#   - Different correlation_ids across chunks are rejected
#   - Inconsistent chunk_total across chunks is rejected
#   - Empty / no-text payloads return [] (no chunking needed)
#   - Fits-in-one-chunk payloads return [] (no chunking needed)
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure v2 importable (conftest does this already in run_all_tests path)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import (
    DEFAULT_CHUNK_SIZE,
    envelope_from_chunks,
    envelope_to_chunks,
    build_envelope,
)


def test_envelope_to_chunks_no_text_returns_empty():
    env = build_envelope("a", "b", "message", {"k": "no text here"})
    chunks = envelope_to_chunks(env)
    assert chunks == [], f"expected no chunks when payload has no text; got {len(chunks)}"


def test_envelope_to_chunks_small_text_returns_empty():
    env = build_envelope("a", "b", "message", {"text": "hi"})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    assert chunks == [], f"expected no chunks when text < max_chunk_size; got {len(chunks)}"


def test_envelope_to_chunks_32kib_split_then_reassemble_roundtrip():
    """64 KiB of text MUST split into exactly 2 chunks of 32 KiB each."""
    big_text = "x" * (DEFAULT_CHUNK_SIZE * 2)  # exactly 2 chunks
    env = build_envelope("claudecode", "codex", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    assert len(chunks) == 2, f"expected 2 chunks, got {len(chunks)}"
    for i, c in enumerate(chunks):
        assert c["correlation_id"] == env["id"], (
            f"chunk {i} correlation_id must equal parent id; got {c['correlation_id']}"
        )
        assert c["in_reply_to"] == env["id"]
        text_chunks = c["payload"]["text_chunks"]
        assert text_chunks[0]["chunk_total"] == 2
        assert text_chunks[0]["chunk_index"] == i
        assert text_chunks[0]["chunk_id"] == env["id"]
    # Reassemble
    parent = envelope_from_chunks(chunks)
    assert parent["payload"]["text"] == big_text, (
        "reassembled text must equal original; "
        f"len(reassembled)={len(parent['payload']['text'])} vs len(orig)={len(big_text)}"
    )
    assert parent["reassembled_from_chunks"] is True
    assert parent["payload"]["chunk_total"] == 2


def test_envelope_to_chunks_64kib_split_then_reassemble_roundtrip():
    """100 KiB should split into ceil(100/32)=4 chunks (32+32+32+4)."""
    big_text = "y" * 102400  # 100 KiB
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    assert len(chunks) == 4, f"expected 4 chunks for 100KB at 32KB, got {len(chunks)}"
    # Reassemble
    parent = envelope_from_chunks(chunks)
    assert parent["payload"]["text"] == big_text
    assert parent["payload"]["chunk_total"] == 4


def test_envelope_from_chunks_rejects_missing_index():
    big_text = "z" * (DEFAULT_CHUNK_SIZE * 3)  # 3 chunks
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    assert len(chunks) == 3
    # Drop chunk index 1
    pruned = [c for c in chunks if c["payload"]["text_chunks"][0]["chunk_index"] != 1]
    raised = False
    try:
        envelope_from_chunks(pruned)
    except ValueError as e:
        raised = True
        assert "missing chunk indices" in str(e), f"unexpected message: {e}"
    assert raised, "expected ValueError for missing chunk index"


def test_envelope_from_chunks_rejects_duplicate_index():
    big_text = "z" * (DEFAULT_CHUNK_SIZE * 3)
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    # Duplicate chunk index 0
    duped = list(chunks) + [chunks[0]]
    raised = False
    try:
        envelope_from_chunks(duped)
    except ValueError as e:
        raised = True
        assert "duplicate chunk_index" in str(e), f"unexpected: {e}"
    assert raised, "expected ValueError for duplicate chunk_index"


def test_envelope_from_chunks_rejects_mismatched_correlation_id():
    big_text = "z" * (DEFAULT_CHUNK_SIZE * 2)
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    # Forge a different correlation_id on the second chunk
    chunks[1]["correlation_id"] = "00000000-0000-4000-8000-000000000000"
    raised = False
    try:
        envelope_from_chunks(chunks)
    except ValueError as e:
        raised = True
        assert "correlation_id" in str(e), f"unexpected: {e}"
    assert raised, "expected ValueError for correlation_id mismatch"


def test_envelope_from_chunks_rejects_inconsistent_chunk_total():
    big_text = "z" * (DEFAULT_CHUNK_SIZE * 3)
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    # Forge inconsistent chunk_total on the second chunk
    chunks[1]["payload"]["text_chunks"][0]["chunk_total"] = 5
    raised = False
    try:
        envelope_from_chunks(chunks)
    except ValueError as e:
        raised = True
        assert "chunk_total" in str(e), f"unexpected: {e}"
    assert raised, "expected ValueError for inconsistent chunk_total"


def test_envelope_from_chunks_rejects_empty():
    raised = False
    try:
        envelope_from_chunks([])
    except ValueError:
        raised = True
    assert raised, "expected ValueError on empty chunk list"


def test_envelope_to_chunks_chunk_id_stable_across_chunks():
    big_text = "a" * (DEFAULT_CHUNK_SIZE * 5)
    env = build_envelope("a", "b", "message", {"text": big_text})
    chunks = envelope_to_chunks(env, max_chunk_size=DEFAULT_CHUNK_SIZE)
    chunk_ids = set(c["payload"]["text_chunks"][0]["chunk_id"] for c in chunks)
    assert chunk_ids == {env["id"]}, f"all chunks must share parent id; got {chunk_ids}"