import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py")
src = p.read_text(encoding="utf-8")
old = '    sem = threading.BoundedSemaphore(MAX_CONCURRENT)\n    stats = ConsumerStats()'
new = '    sem = threading.BoundedSemaphore(MAX_CONCURRENT)\n    # Always initialize stats so early-return paths can include totals.\n    stats = ConsumerStats()'
if old in src:
    src = src.replace(old, new, 1)
    p.write_text(src, encoding="utf-8")
    print("stats init preserved at top of tick")
else:
    print("OLD NOT FOUND - reordering")
