import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py")
src = p.read_text(encoding="utf-8")
# Move stats init BEFORE the recipients filter
old = "    recipients = [r for r in recipients if r != \"codex\"]\n    if not recipients:\n        return {\"ok\": False, \"reason\": \"no_recipients\", \"ticked_at\": _now_iso(), \"totals\": stats.snapshot()}\n\n    sem = threading.BoundedSemaphore(MAX_CONCURRENT)\n    # Always initialize stats so early-return paths can include totals.\n    stats = ConsumerStats()"
new = "    # Always initialize stats first so early-return paths can include totals.\n    stats = ConsumerStats()\n    recipients = [r for r in recipients if r != \"codex\"]\n    if not recipients:\n        return {\"ok\": False, \"reason\": \"no_recipients\", \"ticked_at\": _now_iso(), \"totals\": stats.snapshot()}\n\n    sem = threading.BoundedSemaphore(MAX_CONCURRENT)"
if old in src:
    src = src.replace(old, new)
    p.write_text(src, encoding="utf-8")
    print("stats init moved before early-return check")
else:
    print("OLD NOT FOUND")
