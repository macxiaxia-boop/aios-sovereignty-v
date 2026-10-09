"""Fix v2_consumer.py:465 - replace broken multi-line with single line, AND fix any other \n literals."""
from pathlib import Path
import re

target = Path(r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py")
src = target.read_text(encoding="utf-8")

# Find and replace the broken line (literal \n in source)
broken = '        _gg_step = {"step": "goal_guard", "ok": False, "reason": _gg_risk.get("envelope_type") or _gg_risk.get("reason") or "blocked"}\\n        out["steps"].append(_gg_step)'
fixed = '        out["steps"].append({"step": "goal_guard", "ok": False, "reason": _gg_risk.get("envelope_type", _gg_risk.get("reason", "blocked"))})'

if broken in src:
    new_src = src.replace(broken, fixed)
    target.write_text(new_src, encoding="utf-8")
    print(f"✅ Fixed. File now {len(new_src)} bytes")
else:
    print("NOT FOUND - searching...")
    for i, line in enumerate(src.split("\n")):
        if "goal_guard" in line:
            print(f"  line {i+1}: {line}")

# Also fix any other literal \n that snuck in
src2 = target.read_text(encoding="utf-8")
src2 = re.sub(r'(?<=\w)"\\n\s+', "\n", src2)  # "text"\n -> "text"<newline>
target.write_text(src2, encoding="utf-8")
print(f"After cleanup: {len(src2)} bytes")

# Verify syntax
import ast
try:
    ast.parse(src2)
    print("✅ syntax OK")
except SyntaxError as e:
    print(f"❌ syntax error: {e}")