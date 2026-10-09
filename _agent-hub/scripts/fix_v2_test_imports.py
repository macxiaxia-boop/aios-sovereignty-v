"""fix_v2_test_imports.py — Phase-2 引入的 broken imports."""
import pathlib

# Tests with `from src.queue import ...` — change to `from src.message_queue`
fixes = [
    r"D:\AIOS\_agent-hub\v2\tests\test_02_queue_concurrency.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_05_protocol_loopback.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_10_consumer_dispatch.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_11_consumer_restart_lease.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_15_trace_completeness.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_17_codex_quota_handoff.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_gated_live_smoke_r286.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_goal_guard_hook.py",
]
for p_str in fixes:
    p = pathlib.Path(p_str)
    if not p.exists():
        print(f"  skip (not found): {p_str}")
        continue
    s = p.read_text(encoding="utf-8")
    old = "from src.queue import"
    new = "from src.message_queue import"
    if old in s and new not in s:
        s = s.replace(old, new)
        p.write_text(s, encoding="utf-8")
        print(f"  fixed: {p_str}")
    elif new in s:
        print(f"  already fixed: {p_str}")
    else:
        print(f"  no `from src.queue` in: {p_str}")

# Tests with `from src.message_queue import ...` — leave alone (already correct)
# But verify they don't have a stale `from .queue` that breaks things
for p_str in [
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t15.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t18.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t19.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t20.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t21.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t22.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t23.py",
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t24.py",
]:
    p = pathlib.Path(p_str)
    s = p.read_text(encoding="utf-8")
    if "from src.message_queue import" in s:
        print(f"  ok: {p_str}")