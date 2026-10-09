"""fix_inbound_permission_scope_budget.py — 让 permission_scope.max_budget = goal.budget."""
import pathlib

p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\src\inbound_goal_generation.py")
src = p.read_text(encoding="utf-8")

old = '''    perm = PermissionScope(
        allowed_paths=allowed_paths_seed,
        allowed_ops=list(getattr(intent_scope, "allowed_ops", []) or []),
        max_budget=float(getattr(intent_scope, "max_budget", 0.0) or 0.0),
        max_duration_sec=getattr(intent_scope, "max_duration_sec", None),
        requires_approval=list(getattr(intent_scope, "requires_approval", []) or []),
    )'''

new = '''    # G002-FIX-INDEX: max_budget must equal goal.budget (Goal model cross-validator enforces).
    # intent_scope.max_budget may be 0.0 if parser didn't extract, but goal.budget is authoritative.
    perm = PermissionScope(
        allowed_paths=allowed_paths_seed,
        allowed_ops=list(getattr(intent_scope, "allowed_ops", []) or []),
        max_budget=float(budget),  # use goal's budget (always >= 0)
        max_duration_sec=getattr(intent_scope, "max_duration_sec", None),
        requires_approval=list(getattr(intent_scope, "requires_approval", []) or []),
    )'''

assert old in src, "PermissionScope block not found"
src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("permission_scope.max_budget fixed")