"""test_strategy_gate_submit_task.py — Tests for the Phase-2 correction that
adds a structured strategy-policy gate at the start of
``state_machine.submit_task``.

Verifies that:
  - Valid horizontal marketing submission is accepted and task file written.
  - Retired-id submission (in title, description, OR input_payload) is
    rejected with StrategyGateRejected; no task file written; event logged
    with both ``policy_gate_rejected`` and ``underlying_event_type``.
  - Industry preset submission is rejected with STRATEGY_DRIFT_DETECTED.
  - Deprecated asset submission is rejected with DEPRECATED_ASSET_REFERENCED.
  - Archive leak submission is rejected with ARCHIVE_LEAK_DETECTED.
  - When the policy file is missing, submit_task fails closed with
    ``reason == 'policy_load_failed'``.
  - The event log entry carries both ``POLICY_GATE_REJECTED`` umbrella
    and the underlying event type for any reject path.
  - Existing state_machine behavior (default queued, valid transitions,
    terminal blocks) is preserved by the patch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT.parent / "policy"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from src.goal_guard_hook import clear_strategy_gate_cache  # noqa: E402
from src.paths import EVENTS_LOG, TASKS_DIR  # noqa: E402
from src.state_machine import (  # noqa: E402
    StrategyGateRejected,
    cancel,
    list_tasks,
    submit_task,
    transition,
)


@pytest.fixture(autouse=True)
def _reset_gate_cache():
    """Reset the process-wide strategy gate cache between tests."""
    clear_strategy_gate_cache()
    yield
    clear_strategy_gate_cache()


# ---------------------------------------------------------------- Helpers
def _task_file_set() -> set:
    """Snapshot of current task-file basenames (excludes tmp)."""
    return {
        p.name
        for p in TASKS_DIR.glob("*.json")
        if ".tmp" not in p.name and not p.name.endswith(".tmp")
    }


def _read_event_log_entries() -> list:
    """Return parsed JSON entries from events.ndjson."""
    p = EVENTS_LOG
    if not p.exists():
        return []
    return [
        json.loads(line)
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _find_submit_rejected(title: str) -> "dict | None":
    """Find the task.submit_rejected log entry for a given title."""
    for ev in _read_event_log_entries():
        if (
            ev.get("event") == "task.submit_rejected"
            and ev.get("title") == title
        ):
            return ev
    return None


# ---------------------------------------------------------------- Valid accept
def test_valid_horizontal_marketing_task_accepted():
    """A clean horizontal-marketing task must pass the gate."""
    title = "Plan Q4 SaaS retention campaign"
    before = _task_file_set()
    t = submit_task(
        title=title,
        assignee="codex",
        owner="claudecode",
        description="Use general marketing automation for upsell.",
        input_payload={"goal": "increase retention 5%"},
    )
    assert t["state"] == "queued"
    after = _task_file_set()
    assert after - before == {f"{t['task_id']}.json"}, (
        f"new task file should appear; got {after - before}"
    )
    # No submit_rejected event for this title
    assert _find_submit_rejected(title) is None


# ---------------------------------------------------------------- Retired id rejection
def test_retired_id_in_title_rejected():
    """Submission whose TITLE references a retired id is rejected."""
    title = "Implement R-001 reactivation"
    before = _task_file_set()
    with pytest.raises(StrategyGateRejected) as exc:
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="Per R-001, deploy 23-tool gateway.",
            input_payload={},
        )
    err = exc.value
    assert err.reason == "strategy_gate_blocked"
    event_types = [e.get("event_type") for e in err.events]
    assert "RETIRED_REQUIREMENT_REACTIVATED" in event_types
    # No NEW task file should have been written.
    assert _task_file_set() == before, (
        f"rejected submission must not write task file; "
        f"new files: {_task_file_set() - before}"
    )
    # Event log must contain the structured reject event.
    ev = _find_submit_rejected(title)
    assert ev is not None, "submit_rejected event must be logged"
    assert ev.get("policy_gate_rejected") is True
    assert ev.get("underlying_event_type") == "RETIRED_REQUIREMENT_REACTIVATED"


def test_retired_id_in_description_rejected():
    """Retired id inside description (not title) is still rejected."""
    title = "Marketing automation followup cleanup"
    before = _task_file_set()
    with pytest.raises(StrategyGateRejected):
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="Resume R-009 (装修矩阵 V2) work",
            input_payload={},
        )
    assert _task_file_set() == before
    ev = _find_submit_rejected(title)
    assert ev is not None
    assert ev.get("underlying_event_type") == "RETIRED_REQUIREMENT_REACTIVATED"
    assert "RETIRED_REQUIREMENT_REACTIVATED" in ev.get("all_event_types", [])


def test_retired_id_in_input_payload_rejected():
    """Retired id inside input_payload is still rejected."""
    title = "Worker scope definition"
    before = _task_file_set()
    with pytest.raises(StrategyGateRejected):
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="general scope",
            input_payload={"target": "R-014 followup"},
        )
    assert _task_file_set() == before
    ev = _find_submit_rejected(title)
    assert ev is not None
    assert ev.get("underlying_event_type") == "RETIRED_REQUIREMENT_REACTIVATED"


# ---------------------------------------------------------------- Industry preset rejection
def test_industry_preset_submission_rejected():
    """Submission referencing a blocked industry preset is rejected."""
    title = "Initialize industry-zhuangxiu preset"
    before = _task_file_set()
    with pytest.raises(StrategyGateRejected) as exc:
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="Load the industry preset for the vertical.",
            input_payload={},
        )
    event_types = [e.get("event_type") for e in exc.value.events]
    assert "STRATEGY_DRIFT_DETECTED" in event_types
    assert _task_file_set() == before
    ev = _find_submit_rejected(title)
    assert ev is not None
    assert ev.get("underlying_event_type") == "STRATEGY_DRIFT_DETECTED"


# ---------------------------------------------------------------- Deprecated asset rejection
def test_deprecated_asset_submission_rejected():
    """Submission referencing a deprecated asset path is rejected."""
    title = "Re-point to old gateway entry"
    before = _task_file_set()
    with pytest.raises(StrategyGateRejected) as exc:
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="Use D:\\CloudTech-Portable\\gateway_v22.py as entry",
            input_payload={},
        )
    event_types = [e.get("event_type") for e in exc.value.events]
    assert "DEPRECATED_ASSET_REFERENCED" in event_types
    assert _task_file_set() == before
    ev = _find_submit_rejected(title)
    assert ev is not None
    assert ev.get("underlying_event_type") == "DEPRECATED_ASSET_REFERENCED"


# ---------------------------------------------------------------- Archive leak rejection
def test_archive_leak_submission_rejected():
    """Submission referencing an archived surface is rejected."""
    title = "Pull source from archived surface test"
    before = _task_file_set()
    with pytest.raises(StrategyGateRejected) as exc:
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="Read D:\\AIOS\\AIOS_SOURCE_OF_TRUTH_FINAL\\roadmap\\P3-01.md and re-activate",
            input_payload={},
        )
    event_types = [e.get("event_type") for e in exc.value.events]
    assert ("ARCHIVE_LEAK_DETECTED" in event_types
            or "DEPRECATED_ASSET_REFERENCED" in event_types), (
        f"expected ARCHIVE_LEAK or DEPRECATED_ASSET event; got {event_types}"
    )
    assert _task_file_set() == before
    ev = _find_submit_rejected(title)
    assert ev is not None


# ---------------------------------------------------------------- Fail-closed (policy missing)
def test_fail_closed_when_policy_missing(monkeypatch, tmp_path):
    """When the policy file is missing, submit_task fails closed."""
    fake_dir = tmp_path / "empty-policy"
    fake_dir.mkdir()
    monkeypatch.setenv("AIOS_STRATEGY_POLICY_DIR", str(fake_dir))
    clear_strategy_gate_cache()

    title = "Some task without policy available"
    before = _task_file_set()
    with pytest.raises(StrategyGateRejected) as exc:
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="any content",
            input_payload={},
        )
    err = exc.value
    assert err.reason == "policy_load_failed"
    assert err.policy_id is None
    event_types = [e.get("event_type") for e in err.events]
    assert "POLICY_GATE_REJECTED" in event_types
    assert _task_file_set() == before
    ev = _find_submit_rejected(title)
    assert ev is not None
    assert ev.get("policy_gate_rejected") is True
    assert ev.get("underlying_event_type") == "POLICY_GATE_REJECTED"
    assert ev.get("reason") == "policy_load_failed"


# ---------------------------------------------------------------- Event log shape
def test_submit_rejected_event_has_both_umbrella_and_underlying_keys():
    """Every reject event MUST include both umbrella and underlying event_type.

    The umbrella is conveyed via ``policy_gate_rejected=True`` (always
    present when the gate rejects). The underlying event type is the
    specific gate reason (e.g. ``RETIRED_REQUIREMENT_REACTIVATED``).
    POLICY_GATE_REJECTED appears in all_event_types only on the
    fail-closed path (policy load failure); for specific rejections
    the matched event is the only entry.
    """
    title = "Implement R-001 reactivation second pass"
    with pytest.raises(StrategyGateRejected):
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="per R-001, deploy",
            input_payload={},
        )
    ev = _find_submit_rejected(title)
    assert ev is not None
    # Required keys per Phase-2 correction contract.
    assert "policy_gate_rejected" in ev
    assert "underlying_event_type" in ev
    assert ev["policy_gate_rejected"] is True
    assert ev["underlying_event_type"] == "RETIRED_REQUIREMENT_REACTIVATED"
    assert "RETIRED_REQUIREMENT_REACTIVATED" in ev.get("all_event_types", [])


def test_submit_rejected_event_has_umbrella_when_policy_load_fails(monkeypatch, tmp_path):
    """When policy fails to load, the umbrella POLICY_GATE_REJECTED is in all_event_types."""
    fake_dir = tmp_path / "empty-policy-2"
    fake_dir.mkdir()
    monkeypatch.setenv("AIOS_STRATEGY_POLICY_DIR", str(fake_dir))
    clear_strategy_gate_cache()

    title = "Some task without policy two"
    with pytest.raises(StrategyGateRejected):
        submit_task(
            title=title,
            assignee="codex",
            owner="claudecode",
            description="any content",
            input_payload={},
        )
    ev = _find_submit_rejected(title)
    assert ev is not None
    assert ev["policy_gate_rejected"] is True
    assert ev["underlying_event_type"] == "POLICY_GATE_REJECTED"
    assert "POLICY_GATE_REJECTED" in ev.get("all_event_types", [])


def test_rejected_submission_does_not_break_subsequent_valid_submit():
    """After a rejection, the gate still allows subsequent valid submissions."""
    bad_title = "Implement R-001 attempt three"
    with pytest.raises(StrategyGateRejected):
        submit_task(
            title=bad_title,
            assignee="codex",
            owner="claudecode",
            description="per R-001 again",
            input_payload={},
        )
    good_title = "Send welcome email to new lead"
    t = submit_task(
        title=good_title,
        assignee="codex",
        owner="claudecode",
        description="Generic nurture flow.",
        input_payload={},
    )
    assert t["state"] == "queued"
    # Only one reject event for bad_title; the good submission produces none.
    assert _find_submit_rejected(good_title) is None


# ---------------------------------------------------------------- Backwards compatibility
def test_backwards_compat_simple_titles_still_pass():
    """Trivial titles like 'x' / 'a' / 'b' must continue to pass after patch."""
    t = submit_task(title="x", assignee="codex", owner="claudecode")
    assert t["state"] == "queued"
    t2 = submit_task(title="a", assignee="codex", owner="claudecode")
    assert t2["state"] == "queued"
    t3 = submit_task(title="b", assignee="codex", owner="claudecode")
    assert t3["state"] == "queued"


def test_backwards_compat_full_lifecycle_still_works():
    """submit_task + transition + cancel flow must still work end-to-end."""
    t1 = submit_task(
        title="Build welcome page hero section",
        assignee="codex",
        owner="claudecode",
        description="Marketing homepage hero with CTA.",
    )
    # Cancel from queued state (per VALID_TRANSITIONS in state_machine).
    cancelled = cancel(t1["task_id"], actor="claudecode")
    assert cancelled["state"] == "cancelled"
    # Listed in tasks
    assert any(x["task_id"] == t1["task_id"] for x in list_tasks())

    t2 = submit_task(
        title="Publish newsletter draft",
        assignee="codex",
        owner="claudecode",
        description="Send weekly digest to subscribers.",
    )
    after = transition(t2["task_id"], "running", actor="claudecode")
    assert after["state"] == "running"
    done = transition(
        t2["task_id"], "succeeded", actor="codex",
        output_payload={"delivered": 1234},
    )
    assert done["state"] == "succeeded"
    assert done["output_payload"]["delivered"] == 1234


# ---------------------------------------------------------------- Real policy loader sanity
def test_real_policy_loader_works_via_submit_task_path(monkeypatch):
    """Verify policy loader via the loader's own public API.

    The submit_task gate uses ``strategy_gate_for_root`` which calls
    ``load_strategy_policy``. This test asserts that loader's behavior
    against the real policy SSOT is unchanged: ok=True, hash matches.
    """
    from policy.strategy_policy import load_strategy_policy

    res = load_strategy_policy(POLICY_DIR)
    assert res.ok, f"loader should succeed for real policy; got {res.reason} {res.errors}"
    assert res.policy["policy_id"] == "GLOBAL_PRODUCT_STRATEGY"
    assert res.policy["policy_version"] == "2026-10-08"
    # SHA matches the on-disk file (we don't compare to the sidecar here
    # because the loader already does that internally; res.ok implies it).
    import hashlib
    expected = hashlib.sha256(
        (POLICY_DIR / "product_strategy.v1.json").read_bytes()
    ).hexdigest().upper()
    assert res.sha256 == expected