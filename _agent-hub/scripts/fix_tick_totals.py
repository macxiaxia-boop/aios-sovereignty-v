import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py")
src = p.read_text(encoding="utf-8")
old = '    if not recipients:\n        return {"ok": False, "reason": "no_recipients", "ticked_at": _now_iso()}'
new = '    if not recipients:\n        return {\"ok\": False, \"reason\": \"no_recipients\", \"ticked_at\": _now_iso(), \"totals\": stats.snapshot()}'
assert old in src, "old not found"
src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("tick early-return now includes totals")
