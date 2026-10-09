# v2/tests/test_goal_guard_hook.py — F005 integration tests.
#
# Validates that the v2 consumer (with the F005 GoalGuard Hook inserted)
# correctly:
#   1. Passes complete Goal envelopes through to the dispatcher
#   2. Blocks incomplete Goal envelopes (no dispatch happens)
#   3. Writes a risk envelope to v2/messages/risk/ when blocked
#   4. Auto-PASSes terminal / internal envelopes (no GoalContract check)
#
# Strategy: drive dispatch_envelope() directly with hand-built envelopes
# rather than running the full v2 tick loop.  This keeps the test
# deterministic and isolates the GoalGuard behavior from queue / ack
# plumbing.
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Also pull in the kernel so aios_kernel.governance imports work.
KERNEL_SRC = Path("D:/AIOS/kernel/src").resolve()
if KERNEL_SRC.exists() and str(KERNEL_SRC) not in sys.path:
    sys.path.insert(0, str(KERNEL_SRC))

import pytest  # noqa: E402

from src.envelope import build_envelope  # noqa: E402
from src.paths import INBOX, v2_root  # noqa: E402
from src.message_queue import enqueue  # noqa: E402
from src.v2_consumer import (  # noqa: E402
    CAPABILITIES,
    dispatch_envelope,
    set_dispatcher,
)


# ---------------------------------------------------------------- Helpers
def _build_complete_goal_envelope() -> dict:
    """An envelope carrying a complete Goal payload — must dispatch."""
    goal = {
        "title": "Build a thing",
        "success_criteria": "Live in 2 weeks",
        "budget": 100.0,
        "owner": "codex",
        "status": "Active",
        "permission_scope": {
            "allowed_paths": ["D:/AIOS/_agent-hub/v2/"],
        },
        "failure_modes": [{"name": "quota", "severity": "high"}],
        "missing_evidence": [{"name": "pricing", "required": True}],
        "autonomous_scope": [{"domain": "v2", "action": "dispatch"}],
        "requires_authorization": [{"domain": "kernel", "action": "modify"}],
    }
    return build_envelope(
        "claudecode",
        "codex",
        "message",
        {"text": "Please dispatch", "goal": goal, "__r286_f005_test__": True},
    )


def _build_incomplete_goal_envelope() -> dict:
    """An envelope carrying an incomplete Goal — must be blocked."""
    goal = {
        "title": "Build a thing",
        # missing 9 of 10 required fields → must trigger RISK_BLOCK
    }
    return build_envelope(
        "claudecode",
        "codex",
        "message",
        {"text": "Please dispatch", "goal": goal, "__r286_f005_test__": True},
    )


# ---------------------------------------------------------------- Tests
def test_v2_consumer_with_goal_guard_blocks_incomplete():
    """GoalGuard must block an incomplete envelope BEFORE dispatch."""
    dispatched = []

    def fake_dispatcher(env, *, recipient):
        dispatched.append(env.get("id"))
        return {"ok": True, "echo": True}

    set_dispatcher(fake_dispatcher)

    env = _build_incomplete_goal_envelope()
    res = enqueue(env)
    target_path = INBOX / Path(res["file"]).name
    assert target_path.exists()

    out = dispatch_envelope(target_path, env)
    # The hook fires before any "verify" / "claim" / "dispatch" step.
    assert out["ok"] is False
    step_names = [s.get("step") for s in out["steps"]]
    assert "goal_guard" in step_names, f"missing goal_guard step in {step_names}"
    goal_guard_step = next(s for s in out["steps"] if s["step"] == "goal_guard")
    assert goal_guard_step["verdict"] in ("risk_block", "fatal")
    # Dispatcher MUST NOT have been invoked.
    assert dispatched == [], f"dispatcher was called despite guard block: {dispatched}"

    # A risk envelope must exist in messages/risk/
    risk_dir = v2_root() / "messages" / "risk"
    assert risk_dir.exists(), f"risk dir not created at {risk_dir}"
    risk_files = list(risk_dir.glob("*__goal_guard_risk.json"))
    assert len(risk_files) >= 1, "no risk envelope written"
    # Find one that references our envelope id
    matched = False
    for rf in risk_files:
        data = json.loads(rf.read_text(encoding="utf-8"))
        if data.get("original_envelope_id") == env["id"]:
            matched = True
            assert data["type"] == "goal_guard_risk"
            assert data["verdict"] in ("risk_block", "fatal")
            assert isinstance(data["failed_checks"], list)
            assert len(data["failed_checks"]) >= 1
            break
    assert matched, f"no risk envelope matched our envelope id {env['id']}"


    set_dispatcher(None)  # F005 hook test cleanup
def test_v2_consumer_with_complete_goal_dispatches():
    """GoalGuard must PASS a complete goal envelope so dispatch can run."""
    dispatched = []

    def fake_dispatcher(env, *, recipient):
        dispatched.append(env.get("id"))
        return {"ok": True, "echo": True}

    set_dispatcher(fake_dispatcher)

    env = _build_complete_goal_envelope()
    res = enqueue(env)
    target_path = INBOX / Path(res["file"]).name
    assert target_path.exists()

    out = dispatch_envelope(target_path, env)
    # The complete goal must PASS the guard and reach the dispatcher.
    step_names = [s.get("step") for s in out["steps"]]
    assert "goal_guard" not in step_names, (
        f"goal_guard step should NOT appear when verdict=PASS, got {step_names}"
    )
    # Dispatcher MUST have been invoked.
    assert dispatched == [env["id"]], f"dispatcher not called: {dispatched}"


    set_dispatcher(None)  # F005 hook test cleanup
def test_v2_consumer_with_terminal_envelope_skips_guard():
    """ack / result / status / heartbeat / error MUST auto-PASS (no goal check)."""
    for msg_type in ("ack", "result", "status", "heartbeat", "error"):
        env = build_envelope("claudecode", "codex", msg_type, {"text": "x"})
        res = enqueue(env)
        target_path = INBOX / Path(res["file"]).name
        out = dispatch_envelope(target_path, env)
        # Terminal types hit the early "swallowed" branch and never enter the guard.
        step_names = [s.get("step") for s in out["steps"]]
        assert "goal_guard" not in step_names, (
            f"goal_guard must not run for {msg_type}: {step_names}"
        )


def test_v2_consumer_with_no_goal_payload_skips_guard():
    """A message envelope without payload.goal is not a GoalContract → PASS."""
    dispatched = []

    def fake_dispatcher(env, *, recipient):
        dispatched.append(env.get("id"))
        return {"ok": True}

    set_dispatcher(fake_dispatcher)

    env = build_envelope("claudecode", "codex", "message", {"text": "hello"})
    res = enqueue(env)
    target_path = INBOX / Path(res["file"]).name
    out = dispatch_envelope(target_path, env)
    step_names = [s.get("step") for s in out["steps"]]
    assert "goal_guard" not in step_names, (
        f"goal_guard must not run for no-goal envelopes: {step_names}"
    )
    # And the dispatcher ran.
    assert dispatched == [env["id"]]


    set_dispatcher(None)  # F005 hook test cleanup
def test_v2_consumer_blocks_goal_with_verifier_path_fatal():
    """A goal that wants to touch verifier/ must be FATAL — isolated."""
    goal = {
        "title": "Modify verifier",
        "success_criteria": "y",
        "budget": 1.0,
        "owner": "codex",
        "status": "Active",
        "permission_scope": {
            "allowed_paths": ["D:/AIOS/kernel/src/aios_kernel/verifier/deterministic.py"],
        },
        "failure_modes": [{"name": "x"}],
        "missing_evidence": [{"name": "y", "required": True}],
        "autonomous_scope": [{"domain": "a", "action": "b"}],
        "requires_authorization": [{"domain": "c", "action": "d"}],
    }
    env = build_envelope(
        "claudecode", "codex", "message",
        {"text": "x", "goal": goal, "__r286_f005_test__": True},
    )
    res = enqueue(env)
    target_path = INBOX / Path(res["file"]).name
    out = dispatch_envelope(target_path, env)
    step_names = [s.get("step") for s in out["steps"]]
    assert "goal_guard" in step_names
    goal_guard_step = next(s for s in out["steps"] if s["step"] == "goal_guard")
    assert goal_guard_step["verdict"] == "fatal"
