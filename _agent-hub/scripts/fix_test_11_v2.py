import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\tests\test_11_consumer_restart_lease.py")
src = p.read_text(encoding="utf-8")
old = 'result = tick(recipients=["codex"],'
new = 'result = tick(recipients=["claudecode"],  # R320.7.1 codex is supervisor'
if old in src:
    src = src.replace(old, new)
    p.write_text(src, encoding="utf-8")
    print("test_11 recipients fixed")
else:
    print("OLD NOT FOUND")
