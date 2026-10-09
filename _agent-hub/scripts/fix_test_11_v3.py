import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\tests\test_11_consumer_restart_lease.py")
src = p.read_text(encoding="utf-8")
old = "env = build_envelope(\"claudecode\", \"codex\", \"message\","
new = "env = build_envelope(\"codex\", \"claudecode\", \"message\",  # swap sender/recipient for tick recipients=[claudecode]"
if old in src:
    src = src.replace(old, new)
    p.write_text(src, encoding="utf-8")
    print("test_11 envelopes swapped")
else:
    print("OLD NOT FOUND")
