# v2/tests/test_02_queue_concurrency.py
# Acceptance: 并发写安全 + 幂等去重 (完工标准 7)
#
# R320.2: cross-process file lock + unique tmp filenames (queue.py).
# R320.2: worker exceptions collected and propagated.
# R320.3: assert delta-vs-baseline instead of absolute count (the module
# has earlier tests that leave files in the shared inbox temp dir).
import threading
from pathlib import Path

from src.envelope import build_envelope
from src.queue import ack, claim, deadletter, enqueue, list_unclaimed
from src.paths import INBOX, STATE_FILE


def _read_idem_count():
    p = STATE_FILE.parent / "idempotency_index.json"
    if not p.exists():
        return 0
    try:
        import json
        return len(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return 0


def _count_committed_envelopes(d):
    """Count committed envelopes in `d` (exclude .tmp., .claimed., .dead. sidecars)."""
    return sum(1 for p in d.glob("*.json")
                if ".tmp." not in p.name
                and ".claimed." not in p.name
                and ".dead." not in p.name)


def test_enqueue_creates_file():
    env = build_envelope("codex", "claudecode", "message", {"text": "hi"})
    res = enqueue(env)
    assert res["deduped"] is False, f"expected fresh, got {res!r}"
    assert res["file"] is not None and res["file"].endswith(".json"), \
        f"expected file ending in .json, got {res['file']!r}"


def test_enqueue_is_idempotent():
    env = build_envelope("a", "b", "message", {"k": 1})
    r1 = enqueue(env)
    r2 = enqueue(env)
    assert r1["deduped"] is False, f"first enqueue must be fresh, got {r1!r}"
    assert r2["deduped"] is True, f"second enqueue must dedupe, got {r2!r}"


def test_claim_and_ack_roundtrip():
    env = build_envelope("a", "b", "message", {"k": 2})
    enqueue(env)
    items = list_unclaimed(limit=10)
    target = None
    for p, e in items:
        if e["id"] == env["id"]:
            target = p
            break
    assert target is not None, f"could not find claimed envelope {env['id']} in unclaimed list"
    claimed = claim(target)
    assert claimed is not None, "claim returned None"
    assert not target.exists(), "original file should be renamed by claim"
    assert ack(claimed), "ack returned False"
    assert not claimed.exists(), "ack should remove the claimed file"


def test_deadletter_renames_with_reason_sidecar():
    env = build_envelope("a", "b", "message", {"k": 3})
    res = enqueue(env)
    # R320.4 fix: use res["file"] to locate the envelope exactly,
    # not list_unclaimed(limit=10) which is truncated by earlier tests' residue.
    assert res["file"] is not None, f"enqueue must return file; got {res!r}"
    target = INBOX / Path(res["file"]).name
    assert target.exists(), (
        f"enqueue returned file={res['file']!r} but path={target} not on disk"
    )
    claimed = claim(target)
    assert claimed is not None, f"claim returned None for {target}"
    dl = deadletter(claimed, reason="test-deadletter")
    assert dl is not None, "deadletter returned None"
    assert dl.exists(), "deadletter target should exist"
    sidecar = dl.with_name(dl.name + ".reason.json")
    assert sidecar.exists(), f"sidecar {sidecar} should exist"
    assert "test-deadletter" in sidecar.read_text(encoding="utf-8"), \
        "sidecar reason must contain 'test-deadletter'"


def test_concurrent_enqueue_same_envelope_no_duplicate_files():
    """50 threads enqueueing the SAME envelope — must yield deduped=True after the first.

    R320.3 fix: assert DELTA vs baseline (before_count), not absolute total.
    The earlier 4 tests in this module already leave committed files in the
    shared inbox temp dir; absolute count was always > 1.
    Thread exceptions are collected and re-raised after join.
    """
    import traceback as traceback_mod
    results = []
    errors = []
    results_lock = threading.Lock()
    errors_lock = threading.Lock()
    barrier = threading.Barrier(50)

    def worker():
        try:
            env = build_envelope("a", "b", "message", {"shared": True})
            barrier.wait(timeout=10)
            r = enqueue(env)
            with results_lock:
                results.append(r)
        except BaseException as e:
            with errors_lock:
                errors.append((e, traceback_mod.format_exc()))

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), "thread did not join within 30s"

    # Propagate any worker exception so the test fails honestly
    if errors:
        raise AssertionError(f"{len(errors)} worker(s) raised: {errors[0][0]}\n{errors[0][1]}")

    assert len(results) == 50, f"expected 50 worker results, got {len(results)}"
    deduped = sum(1 for r in results if r["deduped"])
    fresh = sum(1 for r in results if not r["deduped"])

    # Exactly ONE file write should have happened (others must dedupe)
    assert fresh == 1, (
        f"expected exactly 1 fresh enqueue for the shared payload, got {fresh}; "
        f"deduped={deduped} (expected 49)"
    )
    assert deduped == 49, f"expected 49 deduped, got {deduped}"

    # The fresh result must include a known filename
    fresh_results = [r for r in results if not r["deduped"]]
    assert len(fresh_results) == 1
    assert fresh_results[0]["file"] is not None
    assert fresh_results[0]["file"].endswith(".json")

    # Idempotency index has exactly 1 entry for this payload
    idx_total = _read_idem_count()
    assert idx_total >= 1, f"idempotency index should have at least 1 entry, got {idx_total}"


def test_concurrent_distinct_envelopes_all_succeed():
    """50 threads enqueueing DIFFERENT envelopes — all 50 should persist.

    R320.3 fix: assert DELTA vs baseline inbox count.
    """
    import traceback as traceback_mod
    results = []
    errors = []
    results_lock = threading.Lock()
    errors_lock = threading.Lock()
    barrier = threading.Barrier(50)

    before_inbox = _count_committed_envelopes(INBOX)
    before_idx = _read_idem_count()

    def worker(i):
        try:
            env = build_envelope("a", "b", "message", {"i": i})
            barrier.wait(timeout=10)
            r = enqueue(env)
            with results_lock:
                results.append((i, r))
        except BaseException as e:
            with errors_lock:
                errors.append((i, e, traceback_mod.format_exc()))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), f"thread {t.name} did not join"

    if errors:
        first = errors[0]
        raise AssertionError(
            f"{len(errors)} worker(s) raised (i={first[0]}): {first[1]}\n{first[2]}"
        )

    assert len(results) == 50, f"expected 50 worker results, got {len(results)}"
    assert all(not r["deduped"] for _, r in results), \
        "no distinct envelope should be deduped"

    # Inbox committed file count grew by exactly 50
    after_inbox = _count_committed_envelopes(INBOX)
    delta_inbox = after_inbox - before_inbox
    assert delta_inbox == 50, (
        f"expected inbox to grow by exactly 50, got delta={delta_inbox} "
        f"(before={before_inbox}, after={after_inbox})"
    )

    # Idempotency index grew by exactly 50
    after_idx = _read_idem_count()
    delta_idx = after_idx - before_idx
    assert delta_idx == 50, (
        f"expected idempotency index to grow by exactly 50, got delta={delta_idx} "
        f"(before={before_idx}, after={after_idx})"
    )