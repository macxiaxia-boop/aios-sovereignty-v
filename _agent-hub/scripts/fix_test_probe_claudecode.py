"""fix_test_probe_claudecode.py — Round 3: 测试假设 claudecode MCP 不可达, 但 Phase-2 装 MCP 后实际可达.

修法: test 用 monkeypatch 阻止 live CLI call, 这样断言在 controlled environment 下成立.
"""
import pathlib

p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\tests\test_06_probes.py")
src = p.read_text(encoding="utf-8")

old = '''def test_probe_claudecode_mapping_consistency():
    r = probe_claudecode()
    _assert_levels_keys("claudecode", r)
    _assert_reverse_implications("claudecode", r)
    # No hardcoded session_is_cc_main=True (R320.1 fix).
    # No live MCP call attempted → reachable/healthy must be False.
    assert r["reachable"] is False, (
        f"claudecode.reachable must be False without a live MCP call "
        f"(got {r['reachable']})"
    )
    assert r["healthy"] is False'''

new = '''def test_probe_claudecode_mapping_consistency(monkeypatch):
    # Round 3: monkeypatch _resolve_claude_cli to None — blocks live CLI call.
    # Phase-2 装 claudecode MCP 后, 默认 probe 真实跑 `claude --version`, reachable=True.
    # 本 test 假设 "no live MCP call" — 必须 controlled environment.
    import probes
    monkeypatch.setattr(probes, "_resolve_claude_cli", lambda: None)

    r = probe_claudecode()
    _assert_levels_keys("claudecode", r)
    _assert_reverse_implications("claudecode", r)
    # No hardcoded session_is_cc_main=True (R320.1 fix).
    # No live MCP call attempted → reachable/healthy must be False.
    assert r["reachable"] is False, (
        f"claudecode.reachable must be False without a live MCP call "
        f"(got {r['reachable']})"
    )
    assert r["healthy"] is False'''

assert old in src, "test block not found"
src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("test_probe_claudecode_mapping_consistency patched (monkeypatch _resolve_claude_cli)")