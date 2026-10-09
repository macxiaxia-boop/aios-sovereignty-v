"""fix_v2_consumer_step_verdict.py — add verdict to goal_guard step dict."""
import pathlib

p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py")
src = p.read_text(encoding="utf-8")
old = '        out["steps"].append({"step": "goal_guard", "ok": False, "reason": _gg_risk.get("envelope_type", _gg_risk.get("reason", "blocked"))})'
new = '        out["steps"].append({"step": "goal_guard", "ok": False, "verdict": _gg_risk.get("verdict", "risk_block"), "reason": _gg_risk.get("envelope_type", _gg_risk.get("reason", "blocked"))})'
assert old in src, "old block not found"
src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("v2_consumer goal_guard step now has verdict key")
