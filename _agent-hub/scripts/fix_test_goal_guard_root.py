import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\tests\test_goal_guard_hook.py")
src = p.read_text(encoding="utf-8")
inject = """\n\n# Test isolation: AIOS_V2_ROOT -> tmp dir (avoid polluting D:\\AIOS\\_agent-hub\\v2)\nfrom pathlib import Path as _Path\nimport tempfile as _tempfile\nimport os as _os\n_TMP_V2_ROOT = _Path(_tempfile.mkdtemp(prefix='aiosv2_goal_guard_test_'))\n_os.environ['AIOS_V2_ROOT'] = str(_TMP_V2_ROOT)\nprint('test_goal_guard_hook: AIOS_V2_ROOT=', _TMP_V2_ROOT)\n"""
import re
match = re.search(r'^def test_', src, re.MULTILINE)
if match:
    pos = match.start()
    new_src = src[:pos] + inject + src[pos:]
    p.write_text(new_src, encoding="utf-8")
    print("AIOS_V2_ROOT injection added at byte", pos)
else:
    print("no test_ found")
