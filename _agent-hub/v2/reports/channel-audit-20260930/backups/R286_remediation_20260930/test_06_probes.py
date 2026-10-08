# v2/tests/test_06_probes.py
# Acceptance: WorkBuddy/Hermes/OpenClaw/Codex/CC 真实探测 (完工标准 5)
#
# R320.3 fix:
#   1. Levels are NOT forward-monotonic. configured is independent of runtime;
#      only the reverse implications hold:
#        healthy  => reachable
#        reachable => present
#      Tests check those (and NOT configured=>present=>reachable=>healthy).
#   2. codex.reachable is determined ONLY by relay_port_open (the bridge
#      transport is "file-queue + aios-interop MCP"; a live ChatGPT.exe
#      process is at most `present`, not `reachable`).
#
# R286 remediation (channel-audit-20260930):
#   - reachable == relay_open is the SOLE reachable oracle for codex.
#   - chatgpt_alive alone only asserts present=True (no reachable=downgrade).
#   - Only when chatgpt_alive AND relay_open=False do we assert reachable=False,
#     as a redundant safety net (the relay-open check already covers it).
#   - Added test_probe_codex_isolated_relay_down_chatgpt_alive to prove the
#     no-false-negative contract via monkeypatch without touching src/probes.py.
import socket
import subprocess
from unittest import mock

import src.probes as probes
from src.probes import (probe_all, probe_claudecode, probe_codex, probe_hermes,
                         probe_openclaw, probe_workbuddy)

LEVELS = ("configured", "present", "reachable", "healthy")


def _assert_levels_keys(agent_id, r):
    for k in LEVELS:
        assert k in r, f"{agent_id} missing level key {k}"
    assert r["agent_id"] == agent_id
    assert isinstance(r["transport"], str)
    assert "ts" in r
    assert isinstance(r["details"], dict)
    assert isinstance(r["evidence"], list)
    assert isinstance(r["blockers"], list)


def _assert_reverse_implications(agent_id, r):
    """The ONLY valid implications are:
        healthy  => reachable
        reachable => present
    configured is independent (a registry fact)."""
    if r["healthy"]:
        assert r["reachable"], (
            f"{agent_id}: healthy=True requires reachable=True "
            f"(got reachable={r['reachable']})"
        )
    if r["reachable"]:
        assert r["present"], (
            f"{agent_id}: reachable=True requires present=True "
            f"(got present={r['present']})"
        )


def test_probe_openclaw_mapping_consistency():
    r = probe_openclaw()
    _assert_levels_keys("openclaw", r)
    _assert_reverse_implications("openclaw", r)
    # port-open implies reachable (we made a live TCP connect)
    port_open = bool(r["details"].get("port_open"))
    assert r["reachable"] == port_open, (
        f"reachable={r['reachable']} but port_open={port_open}"
    )
    # health == (healthz_status == 200) — exactly
    healthz = r["details"].get("healthz_status")
    expected_healthy = (healthz == 200)
    assert r["healthy"] is expected_healthy, (
        f"healthy={r['healthy']} but healthz_status={healthz}; "
        f"if /healthz was 200, healthy must be True. Update env, do not fake."
    )


def test_probe_codex_mapping_consistency():
    r = probe_codex()
    _assert_levels_keys("codex", r)
    _assert_reverse_implications("codex", r)
    # R286: reachable is decided ONLY by relay_port_open (the bridge
    # transport). ChatGPT.exe alive is at best `present`.
    relay_open = bool(r["details"].get("relay_port_open"))
    assert r["reachable"] is relay_open, (
        f"codex.reachable={r['reachable']} but relay_port_open={relay_open}; "
        f"reachable must follow ONLY relay_port_open, not chatgpt_running"
    )
    chatgpt_alive = bool(r["details"].get("chatgpt_running"))
    # R286: chatgpt_alive alone only raises `present`; it MUST NOT raise
    # `reachable` (that's the relay_open oracle's job). So inside this branch
    # we only assert present=True.
    if chatgpt_alive:
        assert r["present"] is True, (
            f"chatgpt_running=True but present={r['present']}"
        )
    # R286: redundant safety net. When ChatGPT.exe is alive AND the relay
    # port is closed, reachable MUST be False. This is logically implied by
    # `reachable is relay_open` above, but stating it explicitly guards
    # against future regressions that decouple the two checks.
    if chatgpt_alive and not relay_open:
        assert r["reachable"] is False, (
            f"chatgpt_alive=True and relay_open=False but reachable={r['reachable']}; "
            f"ChatGPT.exe process alone is NOT proof of MCP bridge reachable"
        )
    # healthy requires a real health-probe transaction we don't have
    assert r["healthy"] is False, (
        f"codex.healthy must be False until a real health-probe transaction exists"
    )


def test_probe_hermes_mapping_consistency():
    r = probe_hermes()
    _assert_levels_keys("hermes", r)
    _assert_reverse_implications("hermes", r)
    exe_exists = bool(r["details"].get("exe_exists"))
    assert r["present"] == exe_exists
    version_ok = r["details"].get("version_exitcode") == 0
    expected_reachable = exe_exists and version_ok and "exec_error" not in r["details"]
    assert r["reachable"] is expected_reachable, (
        f"reachable={r['reachable']} but exe_exists={exe_exists}, "
        f"version_exitcode={r['details'].get('version_exitcode')}"
    )
    expected_healthy = exe_exists and version_ok
    assert r["healthy"] is expected_healthy


def test_probe_workbuddy_mapping_consistency():
    r = probe_workbuddy()
    _assert_levels_keys("workbuddy", r)
    _assert_reverse_implications("workbuddy", r)
    # WorkBuddy has no live CLI/HTTP transport in this scope.
    assert r["healthy"] is False
    assert r["reachable"] is False


def test_probe_claudecode_mapping_consistency():
    r = probe_claudecode()
    _assert_levels_keys("claudecode", r)
    _assert_reverse_implications("claudecode", r)
    # No hardcoded session_is_cc_main=True (R320.1 fix).
    # No live MCP call attempted → reachable/healthy must be False.
    assert r["reachable"] is False, (
        f"claudecode.reachable must be False without a live MCP call "
        f"(got {r['reachable']})"
    )
    assert r["healthy"] is False


def test_probe_all_includes_all_five_agents_with_4_levels():
    all_agents = probe_all()
    ids = sorted(a["agent_id"] for a in all_agents["agents"])
    assert ids == ["claudecode", "codex", "hermes", "openclaw", "workbuddy"]
    for a in all_agents["agents"]:
        _assert_levels_keys(a["agent_id"], a)
        _assert_reverse_implications(a["agent_id"], a)


def test_probe_codex_isolated_relay_down_chatgpt_alive(monkeypatch=None):
    """R286 isolated regression for codex reachable contract.

    Contract under test:
        relay_port_open=False  AND  ChatGPT.exe 'alive' (in tasklist) AND
        CODEX_PORTABLE_EXE.exists()
            =>  probe_codex()['reachable'] is False

    The test patches only test-visible dependencies (socket.create_connection,
    CODEX_PORTABLE_EXE.exists/stat, subprocess.run for tasklist, and
    _agent_in_registry) so that production src/probes.py runs unmodified —
    this proves the reachable contract holds in the probe code itself, not by
    editing probes.py to fake a False. If probes.py regressed and started
    setting reachable=True based on chatgpt_running, this test would catch it.

    Works with both pytest (uses injected `monkeypatch` fixture) and the
    bundled run_all_tests.py driver (uses unittest.mock.patch + try/finally).
    """
    # 1) Relay port CLOSED: socket.create_connection raises OSError.
    def _closed_connect(addr, timeout=None):
        raise OSError("simulated: relay 19194 closed for isolated test")

    # 2) CODEX_PORTABLE_EXE.exists() == True (with a fake .stat()).
    class _FakeStat:
        st_size = 123456789
    class _FakePortablePath:
        def exists(self):
            return True
        def stat(self):
            return _FakeStat()

    # 3) subprocess.run (for `tasklist ... ChatGPT.exe`) returns text that
    #    contains "ChatGPT.exe" so chatgpt_running=True.
    class _FakeCompleted:
        stdout = (
            b"ChatGPT.exe                    12345 Console                    "
            b"1 99,999 K\r\n"
        )
        stderr = b""
        returncode = 0
    def _fake_run(args, *aargs, **kwargs):
        if isinstance(args, (list, tuple)) and len(args) >= 1:
            if "tasklist" in args[0]:
                return _FakeCompleted()
        return _FakeCompleted()

    # 4) Registry helper — keep stable so 'configured' state doesn't interfere.
    def _fake_registry(agent_id):
        return True

    if monkeypatch is not None:
        # pytest fixture path
        monkeypatch.setattr(socket, "create_connection", _closed_connect)
        monkeypatch.setattr(probes, "CODEX_PORTABLE_EXE", _FakePortablePath())
        monkeypatch.setattr(subprocess, "run", _fake_run)
        monkeypatch.setattr(probes, "_agent_in_registry", _fake_registry)
        try:
            r = probes.probe_codex()
        except Exception:
            raise
    else:
        # stdlib mock.patch path (works with run_all_tests.py driver)
        with mock.patch.object(socket, "create_connection", _closed_connect), \
             mock.patch.object(probes, "CODEX_PORTABLE_EXE", _FakePortablePath()), \
             mock.patch.object(subprocess, "run", _fake_run), \
             mock.patch.object(probes, "_agent_in_registry", _fake_registry):
            r = probes.probe_codex()

    # Invariants we set up — these MUST hold for the test to be meaningful.
    assert r["details"].get("relay_port_open") is False, (
        f"isolated-test invariant violated: relay_port_open should be False; "
        f"got {r['details']}"
    )
    assert r["details"].get("exe_exists") is True, (
        f"isolated-test invariant violated: exe_exists should be True; "
        f"got {r['details']}"
    )
    assert r["details"].get("chatgpt_running") is True, (
        f"isolated-test invariant violated: chatgpt_running should be True; "
        f"got {r['details']}"
    )

    # THE assertion under test: no false-positive reachability.
    assert r["reachable"] is False, (
        f"reachable must be False when relay closed even though ChatGPT.exe "
        f"is 'alive' and the portable exe exists; "
        f"got reachable={r['reachable']}, details={r['details']}"
    )

    # Companion: present stays True (process + exe presence).
    assert r["present"] is True, (
        f"present must be True when ChatGPT.exe alive or exe exists; "
        f"got present={r['present']}, details={r['details']}"
    )

    # healthy still requires a real health-probe transaction.
    assert r["healthy"] is False, (
        f"healthy must remain False without a real health-probe transaction; "
        f"got healthy={r['healthy']}, details={r['details']}"
    )