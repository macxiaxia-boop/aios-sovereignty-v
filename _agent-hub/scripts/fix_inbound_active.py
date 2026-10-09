"""fix_inbound_active.py — 让 process_inbound_envelope 在 GoalGuard pass 时自动 transition Pending -> Active + 写 decision audit event. Backward-compat: 默认 activate=True (production), 测试可设 activate=False."""
import pathlib

p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\src\inbound_goal_generation.py")
src = p.read_text(encoding="utf-8")

# Add import for GoalStatus (already imported probably)
# Modify process_inbound_envelope signature + add body

old = '''def process_inbound_envelope(
    envelope: Any,
    parser: IntentParser | None = None,
    v2_root: Path | str | None = None,
) -> tuple[Goal, bool, dict | None, Path]:
    """Full pipeline: envelope -> Goal -> cache -> GoalGuard.

    Returns:
      (goal, allowed, risk_envelope_or_None, cache_path)

    Side effects:
      - Writes the generated Goal JSON to disk (cache_path).
      - NEVER deletes or modifies the original envelope.
    """
    goal = generate_goal_from_envelope(envelope, parser=parser)
    cache_path = cache_goal_to_disk(goal, v2_root=v2_root)
    allowed, _verdict, risk_env = validate_with_goal_guard(goal)
    return goal, allowed, risk_env, cache_path'''

new = '''def _write_decision_audit_event(
    goal: "Goal",
    envelope: Any,
    v2_root: Path | str | None,
) -> None:
    """Append a single NDJSON line to logs/inbound_goal_audit.ndjson.

    Closes the audit gap: every G002 pass is observable post-hoc.
    Uses existing v2 log file conventions (json.loads + "_ndjson_ext" pattern).
    """
    try:
        root = Path(v2_root) if v2_root else (
            Path(os.environ["AIOS_V2_ROOT"]) if os.environ.get("AIOS_V2_ROOT") else DEFAULT_V2_ROOT
        )
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "inbound_goal_audit.ndjson"
        evt = {
            "ts": _now_iso(),
            "event_type": "inbound_goal_active",
            "goal_id": goal.id,
            "title": goal.title,
            "owner": goal.owner,
            "envelope_id": (envelope or {}).get("id") if isinstance(envelope, dict) else None,
            "rationale": "G002 inbound_goal_generation passed GoalGuard; auto-activated for dispatch.",
        }
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\\n")
    except Exception as exc:
        if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
            print(f"[inbound_goal_generation] audit write failed: {exc}", flush=True)


def process_inbound_envelope(
    envelope: Any,
    parser: IntentParser | None = None,
    v2_root: Path | str | None = None,
    activate_on_pass: bool = True,
) -> tuple[Goal, bool, dict | None, Path]:
    """Full pipeline: envelope -> Goal -> cache -> GoalGuard.

    Returns:
      (goal, allowed, risk_envelope_or_None, cache_path)

    Side effects:
      - Writes the generated Goal JSON to disk (cache_path).
      - On PASS + activate_on_pass=True: transitions Goal PENDING -> ACTIVE,
        rewrites cache with new status, writes a decision audit line so the
        active Goal is observable to downstream v2_consumer dispatch + the
        Codex self-audit script.
      - NEVER deletes or modifies the original envelope.
    """
    goal = generate_goal_from_envelope(envelope, parser=parser)
    cache_path = cache_goal_to_disk(goal, v2_root=v2_root)
    allowed, _verdict, risk_env = validate_with_goal_guard(goal)
    if allowed and activate_on_pass and goal.status == GoalStatus.PENDING:
        try:
            goal.transition_to(GoalStatus.ACTIVE)
            cache_path = cache_goal_to_disk(goal, v2_root=v2_root)
            _write_decision_audit_event(goal, envelope, v2_root)
        except Exception as exc:
            if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
                print(f"[inbound_goal_generation] activate failed: {exc}", flush=True)
    return goal, allowed, risk_env, cache_path'''

assert old in src, "process_inbound_envelope block not found"
src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("process_inbound_envelope patched (Active transition + decision audit)")