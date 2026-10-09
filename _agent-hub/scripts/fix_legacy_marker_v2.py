import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\tests\test_10_consumer_dispatch.py")
src = p.read_text(encoding="utf-8")
# Swap sender/recipient so recipient="claudecode" matches tick(recipients=["claudecode"])
old = "        env = build_envelope(\"claudecode\", \"codex\", \"message\", {\"text\": \"stranded\",\n                                \"__r286_stranded__\": uid})"
new = "        env = build_envelope(\"codex\", \"claudecode\", \"message\", {\"text\": \"stranded\",\n                                \"__r286_stranded__\": uid})  # sender=codex recipient=claudecode for tick match"
if old in src:
    src = src.replace(old, new)
    p.write_text(src, encoding="utf-8")
    print("legacy marker test recipient fixed")
else:
    print("OLD NOT FOUND")
