import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\tests\test_10_consumer_dispatch.py")
src = p.read_text(encoding="utf-8")
# Replace tick(recipients=["codex"]) -> tick(recipients=["claudecode"]) since codex is supervisor (round 4+ R320.7.1 fix)
old = 'result = tick(recipients=["codex"], marker_filter=None)  # default marker filter'
new = 'result = tick(recipients=["claudecode"], marker_filter=None)  # default marker filter (was codex, but R320.7.1 codex is supervisor)'
if old in src:
    src = src.replace(old, new)
old2 = 'result = tick(recipients=["codex"], marker_filter=lambda e: False)  # nothing matches'
new2 = 'result = tick(recipients=["claudecode"], marker_filter=lambda e: False)  # nothing matches'
if old2 in src:
    src = src.replace(old2, new2)
    p.write_text(src, encoding="utf-8")
    print("test recipients codex -> claudecode (R320.7.1)")
else:
    p.write_text(src, encoding="utf-8")
    print("only 1 fix applied")
