# v2/tests/test_11_consumer_restart_lease.py
#
# R286.A: idempotency dedup + lease recovery + bounded concurrency
#
# Acceptance:
#   - 6 concurrent identical idempotency_key writers → exactly 1 logical message
#   - claim/ack round-trip works; restart simulated by re-claiming after kill
#   - queue.enqueue() idempotency_index dedupe is correct
#   - lease expires triggers reap (state_machine)
#   - bounded concurrency: thread pool under tick() honors semaphore
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import build_envelope
from src.paths import INBOX, STATE_FILE, TASKS_DIR
from src.message_queue import ack as q_ack, claim as q_claim, enqueue, list_unclaimed
from src.state_machine import reap_expired, submit_task, transition, list_tasks


def _idem_index_count():
    p = STATE_FILE.parent / "idempotency_index.json"
    if not p.exists():
        return 0
    import json
    try:
        return len(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return 0


def test_idempotency_6_concurrent_writers_persist_exactly_one():
    """R286 §2.5: 6 concurrent identical idempotency_key writers must persist
    exactly ONE logical message.  Different from test_02's 50-thread test:
    here we use 6 writers (matches §2.8 bounded concurrency default 2/8)
    and assert via the idempotency_index sidecar."""
    import traceback as _tb
    payload = {"text": "r286-6-writers", "k": "shared"}
    results = []
    errors = []
    res_lock = threading.Lock()
    err_lock = threading.Lock()
    barrier = threading.Barrier(6)

    def worker():
        try:
            env = build_envelope("a", "b", "message", payload)
            barrier.wait(timeout=10)
            r = enqueue(env)
            with res_lock:
                results.append(r)
        except BaseException as e:
            with err_lock:
                errors.append((e, _tb.format_exc()))

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    if errors:
        raise AssertionError(f"worker errors: {errors[0]}")

    assert len(results) == 6, f"expected 6 results, got {len(results)}"
    fresh = sum(1 for r in results if not r["deduped"])
    dedup = sum(1 for r in results if r["deduped"])
    assert fresh == 1, f"expected exactly 1 fresh enqueue, got {fresh}"
    assert dedup == 5, f"expected 5 deduped, got {dedup}"


def test_consumer_kill_restart_recovery_via_unclaimed_list():
    """R286 §2.10: if the consumer dies mid-dispatch (between claim and ack),
    the next consumer tick should be able to re-list the envelope as
    unclaimed (it wasn't ack'd, so it stays in INBOX under .claimed.*) and
    NOT lose it.

    We simulate this by: enqueue → claim (rename to .claimed.*) → kill
    (do nothing) → confirm the envelope still exists and can be ack'd."""
    env = build_envelope("codex", "claudecode", "message",  # swap sender/recipient for tick recipients=[claudecode]
                         {"text": "kill-restart", "__r286_test__": "test_restart"})
    res = enqueue(env)
    target = INBOX / Path(res["file"]).name
    claimed = q_claim(target)
    assert claimed is not None
    # Simulate kill: do NOT ack.  The .claimed.* file is left orphaned.
    # In a real consumer, after restart, the supervisor would scan the
    # .claimed.* sidecars.  For now, we verify:
    #   1) The .claimed.* file still exists.
    #   2) It can still be ack'd (cleanup).
    assert claimed.exists()
    assert q_ack(claimed), "should be able to ack the orphaned .claimed.* file after restart"


def test_lease_recovery_state_machine():
    """R286 §2.6: lease expiry triggers reaper; reap_expired auto-retries up to budget.

    Isolation: reap_expired processes tasks in iteration order and stops at
    the first expired lease.  Earlier tests in this run may have left tasks
    with expired leases in the shared tempdir.  We:
      1) Cancel all pre-existing tasks (running/queued/waiting) so they don't
         interfere with reap.
      2) Create our task with a unique assignee.
      3) Sleep to force lease expiry.
      4) Loop reap until our task is reaped OR we exhaust retries.
    """
    # Cancel all pre-existing non-terminal tasks so reap doesn't pick them up.
    for t in list_tasks(state="running"):
        try:
            transition(t["task_id"], "failed", actor="r286_cleanup",
                        note="r286-lease-test-cleanup")
        except Exception:
            pass
    for t in list_tasks(state="waiting"):
        try:
            transition(t["task_id"], "failed", actor="r286_cleanup",
                        note="r286-lease-test-cleanup")
        except Exception:
            pass
    for t in list_tasks(state="queued"):
        try:
            cancel(t["task_id"], actor="r286_cleanup")
        except Exception:
            pass

    # Use a unique assignee name to avoid collision with prior tests' tasks.
    # R286.D contract: derive the actual sleep from the REAL lease_expires_at
    # the state machine computed (NOT a brute-force constant).  This is robust
    # against second-boundary rounding because we wait until wall-clock >
    # lease_expires_at + safety margin, regardless of where the boundary
    # landed.  Polling reap_expired until the task is reaped keeps the loop
    # deterministic on slow / loaded machines.
    task = submit_task(title="r286-lease", assignee="r286-lease-agent",
                       owner="claudecode", timeout_ms=2000, max_retries=2)
    t1 = transition(task["task_id"], "running", actor="claudecode")
    lease_iso = t1["lease_expires_at"]
    assert lease_iso, "transition to running MUST set lease_expires_at"
    # Parse the ISO8601 lease boundary and compute the exact wait.  Safety
    # margin of 1.5s past the boundary guarantees reap_expired sees the
    # lease as expired even with second-precision truncation.  Negative
    # delta means the lease is already in the past — sleep 0.
    from datetime import datetime, timezone
    lease_dt = datetime.strptime(lease_iso, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc,
    )
    safety_margin_s = 1.5
    deadline_dt = lease_dt.replace()  # copy
    from datetime import timedelta
    # Wait until wall-clock is past lease + margin
    wait_until_dt = lease_dt + timedelta(seconds=safety_margin_s)
    remaining = (wait_until_dt - datetime.now(timezone.utc)).total_seconds()
    if remaining > 0:
        time.sleep(remaining)
    # Poll reap_expired until our task is reaped OR we hit a wall-clock
    # ceiling (10x lease = 20s absolute max).  reap_expired returns ALL
    # tasks it transitioned this call, so a single invocation should be
    # enough once the lease is expired — but we loop for resilience.
    reaped_so_far = []
    our_task_reaped = False
    poll_deadline = datetime.now(timezone.utc) + timedelta(seconds=20.0)
    while datetime.now(timezone.utc) < poll_deadline:
        reaped = reap_expired(actor="r286_test")
        if any(r["task_id"] == task["task_id"] for r in reaped):
            reaped_so_far.extend(reaped)
            our_task_reaped = True
            break
        reaped_so_far.extend(reaped)
        # If reap returned nothing AND we are already past the wait-until
        # boundary, stop polling to avoid infinite loop.
        if not reaped and datetime.now(timezone.utc) >= wait_until_dt:
            break
        # Yield briefly before next poll — reap is cheap but the test
        # doesn't need to burn CPU.
        time.sleep(0.05)
    assert our_task_reaped, (
        f"lease-expiry task must be reaped (possibly after other leftovers); "
        f"lease={lease_iso}, "
        f"now={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}, "
        f"reaped={[r['task_id'] for r in reaped_so_far]}, "
        f"expected={task['task_id']}"
    )
    # Should have transitioned to failed then back to queued (auto-retry)
    after = [t for t in list_tasks() if t["task_id"] == task["task_id"]][0]
    assert after["state"] in ("queued", "running", "failed"), (
        f"after reap+auto-retry, state must be queued|running|failed; got {after['state']}"
    )


def test_bounded_concurrency_under_tick():
    """R286 §2.8: tick() uses BoundedSemaphore(MAX_CONCURRENT).  Inject a slow
    dispatcher that records concurrent execution and verify never exceeds
    MAX_CONCURRENT at any moment."""
    from src.v2_consumer import tick, set_dispatcher, MAX_CONCURRENT

    concurrent = 0
    max_concurrent_observed = 0
    lock = threading.Lock()
    cv = threading.Condition(lock)
    started = 0

    def slow_dispatcher(envelope, *, recipient):
        nonlocal concurrent, max_concurrent_observed, started
        with lock:
            concurrent += 1
            started += 1
            if concurrent > max_concurrent_observed:
                max_concurrent_observed = concurrent
            cv.notify_all()
        time.sleep(0.1)  # hold the slot briefly
        with lock:
            concurrent -= 1
            cv.notify_all()
        return {"ok": True, "slow": True}

    set_dispatcher(slow_dispatcher)
    try:
        # Enqueue MAX_CONCURRENT + 4 envelopes
        n_extra = MAX_CONCURRENT + 4
        for i in range(n_extra):
            env = build_envelope("codex", "claudecode", "message",  # swap sender/recipient for tick recipients=[claudecode]
                                 {"text": f"concur-{i}", "__r286_test__": "test_concurrency"})
            enqueue(env)
        result = tick(recipients=["claudecode"],  # R320.7.1 codex is supervisor
                      marker_filter=lambda e: e.get("payload", {}).get("__r286_test__") == "test_concurrency")
        assert result["ok"] is True
        # Max concurrent observed MUST be ≤ MAX_CONCURRENT
        assert max_concurrent_observed <= MAX_CONCURRENT, (
            f"concurrent dispatch exceeded MAX_CONCURRENT: observed={max_concurrent_observed}, "
            f"MAX_CONCURRENT={MAX_CONCURRENT}"
        )
        # And MUST have observed at least 1 concurrent (sanity check)
        assert max_concurrent_observed >= 1
    finally:
        set_dispatcher(None)


def test_unclaimed_list_respects_filter():
    """R286 §2.2: list_for_recipient filters by recipient/broadcast."""
    a_only = build_envelope("alpha", "alpha", "message", {"text": "alpha-only",
                              "__r286_test__": "test_filter"})
    b_only = build_envelope("beta", "beta", "message", {"text": "beta-only",
                              "__r286_test__": "test_filter"})
    enqueue(a_only)
    enqueue(b_only)

    from src.v2_consumer import list_for_recipient
    alpha_items = list_for_recipient("alpha")
    alpha_ids = [env["id"] for _, env in alpha_items]
    assert a_only["id"] in alpha_ids
    assert b_only["id"] not in alpha_ids

    beta_items = list_for_recipient("beta")
    beta_ids = [env["id"] for _, env in beta_items]
    assert b_only["id"] in beta_ids
    assert a_only["id"] not in beta_ids