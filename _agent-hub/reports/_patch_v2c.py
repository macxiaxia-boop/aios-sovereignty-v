"""Patch v2_consumer.py tick() to exclude codex from recipients"""
import sys
fp = r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py"
with open(fp, "r", encoding="utf-8") as f:
    src = f.read()

old = '''    # Discover recipients from agents.json if not provided.
    if recipients is None:
        recipients = _load_recipients()
    if not recipients:
        return {"ok": False, "reason": "no_recipients", "ticked_at": _now_iso()}'''

new = '''    # Discover recipients from agents.json if not provided.
    if recipients is None:
        recipients = _load_recipients()
    # R320.7.1: codex is supervisor (reads its own inbox via aiosv2.py receive);
    # consumer must NOT process codex's inbound -- otherwise result/ack from
    # workers get re-dispatched and generate infinite feedback loops.
    recipients = [r for r in recipients if r != "codex"]
    if not recipients:
        return {"ok": False, "reason": "no_recipients", "ticked_at": _now_iso()}'''

if old in src:
    src = src.replace(old, new)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK patched")
else:
    print("FAIL: pattern not found")
    sys.exit(1)