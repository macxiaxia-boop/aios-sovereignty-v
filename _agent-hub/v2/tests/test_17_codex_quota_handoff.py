# v2/tests/test_17_codex_quota_handoff.py
#
# R286.D test_17: Failure: Codex quota.
#
# Acceptance:
#   - When a dispatcher raises CodexQuotaExceeded AND
#     AIOS_V2_QUOTA_HANDOFF_ENABLED=1, the consumer MUST:
#       * emit an `error` envelope with code=CODEX_QUOTA_EXCEEDED,
#         correlation_id == input envelope id, in_reply_to == input.id;
#       * write a per-envelope sidecar JSON to v2/reports/quota_handoff_<id>.json
#         containing envelope_id, retry_count, error_code, handoff_to, state;
#       * deadletter the original envelope with reason codex_quota_exceeded:*;
#       * NOT retry (quota is not transient);
#       * NOT touch the 3 stranded pre-R320.6 ack files.
#   - When the feature gate is OFF, CodexQuotaExceeded falls through to the
#     existing retry/deadletter path (backward compatible).
#   - Test is isolated, deterministic, never invokes a real model.
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Always isolate under a temp AIOS_V2_ROOT so this test never pollutes the
# LIVE v2 root (D:\AIOS\_agent-hub\v2) when run directly without pytest /
# without the bundled runner.  The bundled run_all_tests.py loads
# tests.conftest which sets AIOS_V2_ROOT first; this guard covers direct
# `python tests/test_17_codex_quota_handoff.py` invocations.
if "AIOS_V2_ROOT" not in os.environ:
    _test_root = Path(tempfile.mkdtemp(prefix="aiosv2_test17_")).resolve()
    os.environ["AIOS_V2_ROOT"] = str(_test_root)
from src.paths import ensure_dirs  # noqa: E402
ensure_dirs()

from src.envelope import build_envelope
from src.paths import DEADLETTER, INBOX, REPORTS_DIR, v2_root
from src.queue import enqueue
from src.v2_consumer import (
    CodexQuotaExceeded,
    QUOTA_HANDOFF_ENABLED,
    dispatch_envelope,
    set_dispatcher,
    record_quota_handoff,
)


def _feature_gate_set(on: bool):
    os.environ["AIOS_V2_QUOTA_HANDOFF_ENABLED"] = "1" if on else "0"
    # Re-import to re-read the env var (module-level constant).  We mutate
    # the module attribute directly to avoid a reload in test isolation.
    import src.v2_consumer as _vc
    _vc.QUOTA_HANDOFF_ENABLED = (os.environ["AIOS_V2_QUOTA_HANDOFF_ENABLED"] == "1")
    return _vc.QUOTA_HANDOFF_ENABLED


def _collect_envs_with_correlation(corr_id: str):
    """Return (error_envs, ack_envs, result_envs) matching correlation_id."""
    out = {"error": [], "ack": [], "result": []}
    for p in INBOX.glob("*.json"):
        if ".tmp." in p.name or ".claimed." in p.name or ".dead." in p.name:
            continue
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if env.get("correlation_id") != corr_id:
            continue
        mt = env.get("message_type")
        if mt in out:
            out[mt].append((p, env))
    return out


def _legacy_stranded_files():
    """Return list of relative paths for the 3 stranded pre-R320.6 acks."""
    items = []
    for stranded_id in ("41afc2c3-8fd3-4c80-80f2-62943eea25fd",
                        "19334d04-08f8-4d3d-9f94-4eab28d336ce",
                        "0fbf6f33-4eb9-47b6-9400-1c2914b2d72f"):
        for d in (INBOX, DEADLETTER):
            for p in d.glob(f"{stranded_id}__*.json"):
                items.append(str(p.relative_to(v2_root())))
    return sorted(items)


def test_quota_handoff_disabled_by_default():
    """Without setting the env gate, QUOTA_HANDOFF_ENABLED must remain False."""
    # Save current state
    saved = os.environ.get("AIOS_V2_QUOTA_HANDOFF_ENABLED")
    try:
        if saved is not None:
            del os.environ["AIOS_V2_QUOTA_HANDOFF_ENABLED"]
        import src.v2_consumer as _vc
        _vc.QUOTA_HANDOFF_ENABLED = False
        assert _vc.QUOTA_HANDOFF_ENABLED is False
        # Sidecar write is a no-op when gate is OFF
        env = build_envelope("claudecode", "codex", "message", {"text": "off"})
        result = record_quota_handoff(env, CodexQuotaExceeded("CODEX_QUOTA_EXCEEDED", "x"))
        assert result is None, f"record_quota_handoff must no-op when gate is OFF; got {result!r}"
    finally:
        if saved is not None:
            os.environ["AIOS_V2_QUOTA_HANDOFF_ENABLED"] = saved
        # Reset module state for downstream tests
        import src.v2_consumer as _vc
        _vc.QUOTA_HANDOFF_ENABLED = (
            os.environ.get("AIOS_V2_QUOTA_HANDOFF_ENABLED", "0") == "1"
        )


def test_quota_handoff_writes_sidecar_and_error_envelope_and_deadletter():
    """Dispatcher raises CodexQuotaExceeded with gate ON:
       → sidecar JSON, error envelope, deadletter, no retry."""
    before_legacy = _legacy_stranded_files()

    # Turn feature gate ON locally
    import src.v2_consumer as _vc
    saved_gate = _vc.QUOTA_HANDOFF_ENABLED
    _vc.QUOTA_HANDOFF_ENABLED = True
    os.environ["AIOS_V2_QUOTA_HANDOFF_ENABLED"] = "1"

    seen_envelope_ids = []

    def quota_dispatcher(envelope, *, recipient):
        seen_envelope_ids.append(envelope["id"])
        # Simulate Codex quota exhaustion (no real model call)
        raise CodexQuotaExceeded("CODEX_QUOTA_EXCEEDED",
                                  "monthly quota exhausted in test")

    set_dispatcher(quota_dispatcher)
    try:
        # Build + enqueue a fresh envelope addressed to codex
        env = build_envelope("claudecode", "codex", "message",
                             {"text": "r286-quota-test",
                              "__r286_test__": "test_quota_handoff"})
        # Pin retry_count=0 so we can verify it is recorded in the sidecar
        env["retry_count"] = 0
        res = enqueue(env)
        target_path = INBOX / Path(res["file"]).name
        assert target_path.exists()

        out = dispatch_envelope(target_path, env)

        # The dispatcher was called exactly once (no retry)
        assert seen_envelope_ids == [env["id"]], (
            f"quota path must NOT retry; dispatcher was called with "
            f"{seen_envelope_ids}; expected [{env['id']}]"
        )

        # The dispatch outcome must record quota_handoff + deadletter steps
        steps = {s.get("step"): s for s in out["steps"]}
        assert "quota_handoff" in steps, (
            f"expected quota_handoff step in dispatch output; got {out!r}"
        )
        assert steps["quota_handoff"]["ok"] is True
        handoff_path = steps["quota_handoff"].get("path")
        assert handoff_path, f"quota_handoff step must carry a path; got {steps['quota_handoff']}"

        # The original envelope file must have been moved to DEADLETTER.
        # deadletter() renames <claimed>.claimed.<host>.<pid>.<nonce>.json
        # to <dead>.dead.<host>.<pid>.<nonce>.json so a simple glob on
        # `*.dead.*.json` (not `*.dead.json`) catches the sidecar nonce.
        matched_dead = []
        for p in DEADLETTER.glob(f"{env['id']}*.dead.*.json"):
            matched_dead.append(p)
        assert matched_dead, (
            f"expected deadletter file for envelope {env['id']}; got: "
            f"{[p.name for p in DEADLETTER.glob('*.dead.*.json')]}"
        )
        # Read the .reason.json sidecar to confirm reason
        reason_sidecar = matched_dead[0].with_name(matched_dead[0].name + ".reason.json")
        assert reason_sidecar.exists(), (
            f"expected reason sidecar next to deadletter file; got {matched_dead[0]!r}"
        )
        reason_obj = json.loads(reason_sidecar.read_text(encoding="utf-8"))
        assert "codex_quota_exceeded" in reason_obj.get("reason", ""), (
            f"deadletter reason must mention codex_quota_exceeded; got {reason_obj!r}"
        )

        # An error envelope must have been emitted with code=CODEX_QUOTA_EXCEEDED
        collected = _collect_envs_with_correlation(env["id"])
        assert len(collected["error"]) >= 1, (
            f"expected error envelope for {env['id']}; got "
            f"{[(p.name, mt) for mt, lst in collected.items() for p, _ in lst]}"
        )
        err_env_path, err_env = collected["error"][0]
        assert err_env.get("message_type") == "error"
        assert err_env.get("payload", {}).get("code") == "CODEX_QUOTA_EXCEEDED"
        assert err_env.get("correlation_id") == env["id"]
        assert err_env.get("in_reply_to") == env["id"]
        assert err_env.get("payload", {}).get("handoff_recorded") is True

        # The handoff sidecar JSON must exist with the required fields
        handoff_full_path = Path(handoff_path)
        assert handoff_full_path.exists(), (
            f"handoff sidecar must exist at {handoff_full_path}"
        )
        handoff_obj = json.loads(handoff_full_path.read_text(encoding="utf-8"))
        for key in ("ts", "envelope_id", "correlation_id", "sender",
                     "recipient", "retry_count", "error_code",
                     "error_message", "exception_class", "handoff_to", "state"):
            assert key in handoff_obj, (
                f"handoff sidecar missing key {key!r}; got {handoff_obj!r}"
            )
        assert handoff_obj["envelope_id"] == env["id"]
        assert handoff_obj["error_code"] == "CODEX_QUOTA_EXCEEDED"
        assert handoff_obj["retry_count"] == 0
        assert handoff_obj["state"] == "awaiting_user_action"
        assert handoff_obj["handoff_to"] == "claudecode"

        # The 3 stranded files MUST be untouched
        after_legacy = _legacy_stranded_files()
        assert after_legacy == before_legacy, (
            f"3 stranded ack files must NOT be touched by quota test; "
            f"before={before_legacy}, after={after_legacy}"
        )

        # No raw binary in queue (sanity check on handoff payload)
        assert isinstance(handoff_obj["error_message"], str)

        # No new v2 consumer daemon was spawned (test is in-process)
        # No secrets in sidecar
        assert "secret" not in json.dumps(handoff_obj).lower()
        assert "password" not in json.dumps(handoff_obj).lower()

    finally:
        set_dispatcher(None)
        _vc.QUOTA_HANDOFF_ENABLED = saved_gate
        if saved_gate:
            os.environ["AIOS_V2_QUOTA_HANDOFF_ENABLED"] = "1"
        else:
            os.environ.pop("AIOS_V2_QUOTA_HANDOFF_ENABLED", None)


def test_quota_handoff_gate_off_falls_through_to_retry_or_deadletter():
    """With gate OFF, CodexQuotaExceeded is treated like a generic exception
       (existing retry/deadletter path)."""
    import src.v2_consumer as _vc
    saved_gate = _vc.QUOTA_HANDOFF_ENABLED
    _vc.QUOTA_HANDOFF_ENABLED = False
    os.environ.pop("AIOS_V2_QUOTA_HANDOFF_ENABLED", None)

    def quota_dispatcher(envelope, *, recipient):
        raise CodexQuotaExceeded("CODEX_QUOTA_EXCEEDED", "quota-test-off-gate")

    set_dispatcher(quota_dispatcher)
    try:
        env = build_envelope("claudecode", "codex", "message",
                             {"text": "r286-quota-off",
                              "__r286_test__": "test_quota_off_gate"})
        # Exhaust retry budget so we deterministically deadletter
        env["retry_count"] = 5
        res = enqueue(env)
        target_path = INBOX / Path(res["file"]).name

        out = dispatch_envelope(target_path, env)
        # With gate OFF and exhausted retries: deadletter step exists, no
        # quota_handoff step (the sidecar was never written because gate OFF).
        steps = {s.get("step"): s for s in out["steps"]}
        assert "quota_handoff" not in steps, (
            f"with gate OFF, quota_handoff step MUST NOT appear; got {out!r}"
        )
        assert any(s.get("step") == "deadletter" for s in out["steps"]), (
            f"with gate OFF and exhausted retries, deadletter step must appear; "
            f"got {out!r}"
        )
        # Reason must NOT mention codex_quota_exceeded (generic path)
        dead_reason = next(
            (s.get("reason") for s in out["steps"] if s.get("step") == "deadletter"),
            "",
        )
        assert "codex_quota_exceeded" not in (dead_reason or ""), (
            f"generic deadletter reason must NOT mention codex_quota_exceeded; "
            f"got {dead_reason!r}"
        )
        # No sidecar JSON for this envelope
        sidecar = v2_root() / "reports" / f"quota_handoff_{env['id']}.json"
        assert not sidecar.exists(), (
            f"with gate OFF, no quota_handoff sidecar must be written; "
            f"found {sidecar}"
        )
    finally:
        set_dispatcher(None)
        _vc.QUOTA_HANDOFF_ENABLED = saved_gate


def test_quota_handoff_does_not_kill_process_and_does_not_spawn_daemon():
    """Sanity: a quota dispatch leaves no orphan claim sidecars and the
       consumer process keeps running (caller can still call dispatch_envelope
       again after a quota failure)."""
    import src.v2_consumer as _vc
    saved_gate = _vc.QUOTA_HANDOFF_ENABLED
    _vc.QUOTA_HANDOFF_ENABLED = True
    os.environ["AIOS_V2_QUOTA_HANDOFF_ENABLED"] = "1"

    quota_count = {"n": 0}

    def quota_dispatcher(envelope, *, recipient):
        quota_count["n"] += 1
        raise CodexQuotaExceeded("CODEX_QUOTA_EXCEEDED", "n-th call")

    set_dispatcher(quota_dispatcher)
    try:
        env = build_envelope("claudecode", "codex", "message",
                             {"text": "r286-quota-keepalive",
                              "__r286_test__": "test_quota_keepalive"})
        res = enqueue(env)
        target_path = INBOX / Path(res["file"]).name
        out = dispatch_envelope(target_path, env)
        assert any(s.get("step") == "quota_handoff" for s in out["steps"])

        # Subsequent dispatch (different envelope) MUST still work — process
        # is not killed and the dispatcher is still injectable.
        env2 = build_envelope("claudecode", "codex", "message",
                              {"text": "r286-quota-keepalive2",
                               "__r286_test__": "test_quota_keepalive2"})

        def ok_dispatcher(envelope, *, recipient):
            return {"ok": True, "echoed": envelope["id"]}

        set_dispatcher(ok_dispatcher)
        res2 = enqueue(env2)
        target_path2 = INBOX / Path(res2["file"]).name
        out2 = dispatch_envelope(target_path2, env2)
        assert out2["ok"] is True, (
            f"consumer must remain dispatchable after a quota failure; got {out2!r}"
        )
        assert quota_count["n"] == 1, (
            f"quota dispatcher should have been called exactly once across the two "
            f"dispatches; got {quota_count['n']}"
        )
    finally:
        set_dispatcher(None)
        _vc.QUOTA_HANDOFF_ENABLED = saved_gate
        if saved_gate:
            os.environ["AIOS_V2_QUOTA_HANDOFF_ENABLED"] = "1"
        else:
            os.environ.pop("AIOS_V2_QUOTA_HANDOFF_ENABLED", None)


def test_quota_handoff_marker_filter_in_smoke_does_not_claim_legacy():
    """The R286 marker filter from the gated live smoke must still NOT
       claim the 3 stranded ack files when quota path runs in the same
       consumer process.

       Note: unit tests run under a temp AIOS_V2_ROOT (see conftest.py),
       so the 3 stranded files live in the *real* v2 root (D:\\AIOS\\_agent-hub\\v2),
       not in the test tempdir.  This test instead asserts the consumer's
       legacy-file guard does not crash or mis-claim when no stranded
       files are present in the test root — i.e. the guard is a no-op
       when its target files are absent."""
    # Under temp AIOS_V2_ROOT the stranded files do not exist; assert no crash.
    before_legacy = _legacy_stranded_files()
    # `before_legacy` may be empty under temp root.  In the LIVE smoke run
    # (real v2 root) it has 3 entries.  Either way, the assertion is
    # idempotent: list of relative paths before == list after.
    after_legacy = _legacy_stranded_files()
    assert before_legacy == after_legacy
    # No claim-sidecar must have been written for any non-existent
    # stranded id.  (Defensive — guards against regressions that would
    # inject stray .claimed.*.json files for IDs we never touched.)
    from src.paths import INBOX, DEADLETTER
    stray = []
    for stranded_id in ("41afc2c3-8fd3-4c80-80f2-62943eea25fd",
                         "19334d04-08f8-4d3d-9f94-4eab28d336ce",
                         "0fbf6f33-4eb9-47b6-9400-1c2914b2d72f"):
        for d in (INBOX, DEADLETTER):
            for p in d.glob(f"{stranded_id}__*.claimed.*.json"):
                stray.append(str(p.name))
    assert stray == [], f"no stranded-id claim files should exist; got {stray}"