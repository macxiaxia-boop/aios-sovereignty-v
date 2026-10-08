import re
fp = r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py"
with open(fp, "r", encoding="utf-8") as f:
    src = f.read()

# 找块: 从 'if stats is None:' 到 'out = {"ok": False' 之间的内容
# 并把 'out = {"ok"...' 提前
pattern = re.compile(
    r'    if stats is None:\n        stats = ConsumerStats\(\)\n\n    # R320\.7 loop-guard.*?return out\n\n    out = \{"ok": False, "envelope_id": env\.get\("id"\),\n           "steps": \[\]\}\n',
    re.DOTALL
)
def repl(m):
    body = m.group(0)
    # Move the 'out = {...}' before the if stats block
    out_def = '    out = {"ok": False, "envelope_id": env.get("id"),\n           "steps": []}\n    if stats is None:\n        stats = ConsumerStats()\n\n    '
    return out_def + body.split('# R320.7 loop-guard')[0].split('return out\n\n    ')[1].lstrip()

# Simpler: do direct text replacement on the matched prefix
prefix_pattern = re.compile(
    r'    if stats is None:\n        stats = ConsumerStats\(\)\n\n    # R320\.7 loop-guard: terminal message types \(result/ack/status/heartbeat/error\)\n    # MUST NOT trigger another ack or result envelope, or the consumer.s\n    # passthrough dispatcher creates an infinite feedback loop \(each ack\n    # generates a new result which generates a new ack which \.\.\. inbox\n    # exploded from 14 to 5400\+ within ~30 min\)\.\n    TERMINAL_TYPES = \{"result", "ack", "status", "heartbeat", "error"\}\n    if env\.get\("message_type"\) in TERMINAL_TYPES:\n        # Claim the file and just delete it \(q_ack\)\.  No ack_envelope,\n        # no result_envelope\.  This breaks the loop\.\n        claimed = q_claim\(env_path\)\n        if claimed is None:\n            out\["steps"\]\.append\(\{"step": "claim", "ok": False, "reason": "race_lost"\}\)\n            return out\n        out\["steps"\]\.append\(\{"step": "claim", "ok": True, "claimed_path": str\(claimed\.name\)\}\)\n        stats\.incr\("claimed"\)\n        if q_ack\(claimed\):\n            out\["steps"\]\.append\(\{"step": "q_ack", "ok": True, "terminal": True\}\)\n        else:\n            out\["steps"\]\.append\(\{"step": "q_ack", "ok": False\}\)\n        out\["ok"\] = True\n        _log_event\(\{"actor": "v2_consumer", "event": "terminal\.swallowed",\n                    "envelope_id": env\.get\("id"\),\n                    "message_type": env\.get\("message_type"\)\}\)\n        return out\n\n    out = \{"ok": False, "envelope_id": env\.get\("id"\),\n           "steps": \[\]\}\n'
)
new_prefix = (
    '    out = {"ok": False, "envelope_id": env.get("id"),\n           "steps": []}\n'
    '    if stats is None:\n'
    '        stats = ConsumerStats()\n\n'
    '    # R320.7 loop-guard: terminal message types (result/ack/status/heartbeat/error)\n'
    '    # MUST NOT trigger another ack or result envelope, or the consumer\'s\n'
    '    # passthrough dispatcher creates an infinite feedback loop (each ack\n'
    '    # generates a new result which generates a new ack which ... inbox\n'
    '    # exploded from 14 to 5400+ within ~30 min).\n'
    '    TERMINAL_TYPES = {"result", "ack", "status", "heartbeat", "error"}\n'
    '    if env.get("message_type") in TERMINAL_TYPES:\n'
    '        # Claim the file and just delete it (q_ack).  No ack_envelope,\n'
    '        # no result_envelope.  This breaks the loop.\n'
    '        claimed = q_claim(env_path)\n'
    '        if claimed is None:\n'
    '            out["steps"].append({"step": "claim", "ok": False, "reason": "race_lost"})\n'
    '            return out\n'
    '        out["steps"].append({"step": "claim", "ok": True, "claimed_path": str(claimed.name)})\n'
    '        stats.incr("claimed")\n'
    '        if q_ack(claimed):\n'
    '            out["steps"].append({"step": "q_ack", "ok": True, "terminal": True})\n'
    '        else:\n'
    '            out["steps"].append({"step": "q_ack", "ok": False})\n'
    '        out["ok"] = True\n'
    '        _log_event({"actor": "v2_consumer", "event": "terminal.swallowed",\n'
    '                    "envelope_id": env.get("id"),\n'
    '                    "message_type": env.get("message_type")})\n'
    '        return out\n'
)
m = prefix_pattern.search(src)
if not m:
    print("FAIL: prefix pattern not found")
    raise SystemExit(1)
new_src = src[:m.start()] + new_prefix + src[m.end():]
with open(fp, "w", encoding="utf-8") as f:
    f.write(new_src)
print("v2_consumer.py patched OK")
