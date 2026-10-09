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
    # R320.3: reachable is decided ONLY by relay_port_open (the bridge
    # transport). ChatGPT.exe alive is at best `present`.
    relay_open = bool(r["details"].get("relay_port_open"))
    assert r["reachable"] is relay_open, (
        f"codex.reachable={r['reachable']} but relay_port_open={relay_open}; "
        f"reachable must follow ONLY relay_port_open, not chatgpt_running"
    )
    chatgpt_alive = bool(r["details"].get("chatgpt_running"))
    # chatgpt_running may raise present but never reachable
    if chatgpt_alive:
        assert r["present"] is True, (
            f"chatgpt_running=True but present={r['present']}"
        )
        assert r["reachable"] is False, (
            f"chatgpt_running=True but reachable={r['reachable']}; "
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