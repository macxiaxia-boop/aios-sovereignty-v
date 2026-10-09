"""fix_probe_test_v3.py — Round 3: monkeypatch src.probes._resolve_claude_cli."""
import pathlib

p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\tests\test_06_probes.py")
src = p.read_text(encoding="utf-8")

old = "    import probes\n    monkeypatch.setattr(probes, \"_resolve_claude_cli\", lambda: None)"
new = "    monkeypatch.setattr(\"src.probes._resolve_claude_cli\", lambda: None)"

assert old in src, "old block not found"
src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("patched")