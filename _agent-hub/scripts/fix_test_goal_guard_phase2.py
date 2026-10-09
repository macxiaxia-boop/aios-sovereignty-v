"""fix_test_goal_guard.py — Phase-2 Strategy Gate 适配."""
import pathlib

p = pathlib.Path(r"D:\AIOS\kernel\tests\unit\test_goal_guard.py")
src = p.read_text(encoding="utf-8")

# Fix 1: test_hook_layer_block_incomplete_goal
old1 = '''    env = {
        "message_type": "task",
        "id": "env-blocked",
        "payload": {
            "goal": {
                "title": "Build a thing",
                # missing 9 of 10 required fields
            }
        },
    }
    allowed, risk = guard_dispatch(env, ".")
    assert allowed is False
    assert risk is not None
    assert risk["type"] == "goal_guard_risk"
    assert risk["verdict"] in ("risk_block", "fatal")
    assert risk["original_envelope_id"] == "env-blocked"'''

new1 = '''    env = {
        "message_type": "task",
        "id": "env-blocked",
        "payload": {
            "title": "Build a thing",  # Phase-2: Strategy Gate requires payload.title
            "text": "Build a thing",
            "goal": {
                "title": "Build a thing",
                # missing 9 of 10 required fields
            }
        },
    }
    allowed, risk = guard_dispatch(env, ".")
    assert allowed is False
    assert risk is not None
    assert risk["type"] == "goal_guard_risk"
    assert risk["verdict"] in ("risk_block", "fatal")
    assert risk["original_envelope_id"] == "env-blocked"'''

assert old1 in src, "block1 not found"
src = src.replace(old1, new1)

# Fix 2: test_hook_layer_block_goal_with_verifier_path
old2 = '''        "payload": {
            "goal": {
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
        },
    }
    allowed, risk = guard_dispatch(env, ".")
    assert allowed is False
    assert risk["verdict"] == "fatal"'''

new2 = '''        "payload": {
            "title": "Modify verifier",  # Phase-2: Strategy Gate requires payload.title
            "text": "Modify verifier",
            "goal": {
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
        },
    }
    allowed, risk = guard_dispatch(env, ".")
    assert allowed is False
    assert risk["type"] == "goal_guard_risk"
    assert risk["verdict"] == "fatal"'''

assert old2 in src, "block2 not found"
src = src.replace(old2, new2)

# Fix 3: test_hook_layer_pass_complete_goal
old3 = '''        "payload": {
            "goal": {
                "title": "OK",
                "success_criteria": "Live",'''

new3 = '''        "payload": {
            "title": "OK",  # Phase-2: Strategy Gate requires payload.title
            "text": "OK complete task",
            "goal": {
                "title": "OK",
                "success_criteria": "Live",'''

assert old3 in src, "block3 not found"
src = src.replace(old3, new3)

p.write_text(src, encoding="utf-8")
print("test_goal_guard 3 tests fixed")