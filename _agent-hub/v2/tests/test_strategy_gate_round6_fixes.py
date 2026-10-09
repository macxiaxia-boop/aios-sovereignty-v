#!/usr/bin/env python3
# v2/tests/test_strategy_gate_round6_fixes.py
# Covers A-1 through A-8 fixes from 2026-10-09_STRATEGY_GATE_AUDIT.md
from __future__ import annotations

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent  # D:\AIOS\_agent-hub
sys.path.insert(0, str(PARENT))
sys.path.insert(0, str(ROOT))  # D:\AIOS\_agent-hub\v2

# Load policy as package + envelope helper
import policy
import policy.strategy_gate as sg
from src.envelope import build_envelope
from src.goal_guard_hook import envelope_to_contract

POLICY_PATH = PARENT / "policy" / "product_strategy.v1.json"


def _make_gate():
    policy_data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return sg.StrategyGate(policy=policy_data)


def _build_text_envelope(text: str, recipient: str = "claudecode"):
    return build_envelope("codex", recipient, "task", {
        "title": "Round 6 audit test envelope",
        "text": text,
        "evidence_marker": f"AUDIT6-{text[:20]}",
    })


def test_a1_prohibited_active_asset_blocks():
    gate = _make_gate()
    env = _build_text_envelope("minimax-cn is used here for legacy compatibility")
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed, f"PA-09 should block, got allowed={decision.allowed}"
    pa_events = [e for e in decision.events if e.event_type == "DEPRECATED_ASSET_REFERENCED"]
    assert pa_events, f"Expected DEPRECATED_ASSET_REFERENCED event, got {[e.event_type for e in decision.events]}"
    print(f"  OK A-1: PA-09 blocked ({len(pa_events)} events)")


def test_a2_quarantine_path_blocks():
    gate = _make_gate()
    env = _build_text_envelope("see C:\\Users\\xinzh\\.workbuddy\\memory\\45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md for details")
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed, f"quarantine path should block, got allowed={decision.allowed}"
    qp_events = [e for e in decision.events if e.event_type == "DEPRECATED_ASSET_REFERENCED"]
    assert qp_events, f"Expected DEPRECATED_ASSET_REFERENCED for quarantine, got events={[e.event_type for e in decision.events]}"
    print(f"  OK A-2: quarantine_paths blocked ({len(qp_events)} events)")


def test_a3_non_dict_payload_blocks():
    gate = _make_gate()
    env = build_envelope("codex", "claudecode", "task", [1, 2, 3])
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed, f"non-dict payload should block, got allowed={decision.allowed}"
    type_events = [e for e in decision.events if e.event_type == "INVALID_TASK_GENERATED"]
    assert type_events, f"Expected INVALID_TASK_GENERATED, got events={[e.event_type for e in decision.events]}"
    assert "payload_type" in str(type_events[0].matched_id), f"Expected payload_type in matched_id, got {type_events[0].matched_id}"
    print(f"  OK A-3: non-dict task payload blocked")


def test_a3b_non_empty_string_payload_blocks():
    gate = _make_gate()
    env = build_envelope("codex", "claudecode", "task", "just a string")
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed, "non-empty string payload should block"
    print(f"  OK A-3b: str payload blocked")


def test_a4_nested_input_payload_goal_extracted():
    env = build_envelope("codex", "claudecode", "task", {
        "title": "should be ignored",
        "input_payload": {
            "goal": {
                "title": "actual title from nested",
                "success_criteria": ["test passes"],
            }
        }
    })
    contract = envelope_to_contract(env)
    assert contract is not None, f"Should extract nested contract, got None"
    assert contract.get("title") == "actual title from nested", f"Wrong title: {contract.get('title')}"
    print(f"  OK A-4: nested input_payload.goal extracted")


def test_a5_case_insensitive_alias():
    gate = _make_gate()
    env = _build_text_envelope("we still have cloudtech v22 installed")
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed, f"case-insensitive should match, got allowed={decision.allowed}"
    print(f"  OK A-5: case-insensitive alias match works")


def test_a6_event_vocab_dynamic():
    policy_data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    policy_vocab = set(policy_data.get("gate_event_types", []))
    assert "POLICY_GATE_REJECTED" in policy_vocab
    assert "STRATEGY_DRIFT_DETECTED" in policy_vocab
    print(f"  OK A-6: policy has {len(policy_vocab)} event types in vocabulary")


def test_a7_terminal_message_bypasses_gate():
    gate = _make_gate()
    env = build_envelope("codex", "claudecode", "result", {
        "text": "R-001 R-007 cloudtech v22 minimax legacy tokens here"
    })
    decision = gate.evaluate_envelope(env)
    assert decision.allowed, f"Terminal result should bypass gate, got allowed={decision.allowed}"
    assert decision.reason == "internal_terminal_bypass", f"Wrong reason: {decision.reason}"
    print(f"  OK A-7: terminal result bypasses gate (reason={decision.reason})")


def test_a8_r_id_flexible_format():
    gate = _make_gate()
    env = _build_text_envelope("referencing R-007 explicitly")
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed, f"R-007 should block, got allowed={decision.allowed}"
    print(f"  OK A-8: R-007 (standard 3-digit) detected")


if __name__ == "__main__":
    tests = [
        test_a1_prohibited_active_asset_blocks,
        test_a2_quarantine_path_blocks,
        test_a3_non_dict_payload_blocks,
        test_a3b_non_empty_string_payload_blocks,
        test_a4_nested_input_payload_goal_extracted,
        test_a5_case_insensitive_alias,
        test_a6_event_vocab_dynamic,
        test_a7_terminal_message_bypasses_gate,
        test_a8_r_id_flexible_format,
    ]
    failures = []
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failures.append((t.__name__, str(e)))
    if failures:
        print(f"=== {len(failures)} FAILURES ===")
        for name, err in failures:
            print(f"  - {name}: {err}")
        sys.exit(1)
    print(f"=== ALL {len(tests)} ROUND 6 FIX TESTS PASSED ===")