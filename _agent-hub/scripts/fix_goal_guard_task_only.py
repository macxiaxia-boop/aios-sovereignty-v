import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py")
src = p.read_text(encoding="utf-8")
old = '    # Phase G G002: generic inbound envelope -> GoalContract + 5-check GoalGuard.\n    try:  # fail-open: any error here continues to existing F005 + strategy-gate logic\n        from src.inbound_goal_generation import process_inbound_envelope\n        _g, _ok, _risk, _ = process_inbound_envelope(envelope, v2_root=v2_root)\n        if not _ok:\n            return False, _risk\n    except Exception as exc:\n        if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":\n            print(f"[goal_guard_hook] G002 failed: {exc}", flush=True)'
new = '    # Phase G G002 + Round 4 fix: only "task" message_type triggers GoalGuard.\n    # Other types (message/status/heartbeat/result/ack/error) bypass GoalGuard\n    # and flow directly to strategy-gate + route dispatch.\n    if msg_type == "task":\n        try:\n            from src.inbound_goal_generation import process_inbound_envelope\n            _g, _ok, _risk, _ = process_inbound_envelope(envelope, v2_root=v2_root)\n            if not _ok:\n                return False, _risk\n        except Exception as exc:\n            if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":\n                print(f"[goal_guard_hook] G002 failed: {exc}", flush=True)'
if old in src:
    src = src.replace(old, new)
    p.write_text(src, encoding="utf-8")
    print("GoalGuard restricted to task only")
else:
    print("OLD NOT FOUND")
