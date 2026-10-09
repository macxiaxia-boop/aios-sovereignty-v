import pathlib
p = pathlib.Path(r"D:\AIOS\_agent-hub\v2\tests\test_07_healthcheck.py")
content = p.read_text(encoding="utf-8")
if "_test_07_isolated_v2_root" in content:
    print("already added")
else:
    pos = content.find("def test_")
    if pos >= 0:
        inject = chr(10)+chr(10)+chr(35)+" Test isolation: each test gets its own AIOS_V2_ROOT"+chr(10)
        inject += chr(35)+" in the same pytest session dont pollute shared dirs"+chr(10)
        inject += "import os as _os"+chr(10)+"import shutil as _shutil"+chr(10)+"import tempfile as _tempfile"+chr(10)
        inject += "from pathlib import Path as _Path"+chr(10)+"import pytest as _pytest"+chr(10)+chr(10)
        inject += "@_pytest.fixture(autouse=True)"+chr(10)
        inject += "def _test_07_isolated_v2_root(monkeypatch):"+chr(10)
        inject += "    tmp = _Path(_tempfile.mkdtemp(prefix='"+chr(39)+"a"+chr(39)+"test07_v2_root_"+chr(39)+"a"+chr(39)+"')).resolve()"+chr(10)
        inject += "    monkeypatch.setenv("+chr(39)+"a"+chr(39)+"AIOS_V2_ROOT"+chr(39)+"a"+chr(39)+", str(tmp))"+chr(10)
        inject += "    yield"+chr(10)
        inject += "    _shutil.rmtree(str(tmp), ignore_errors=True)"+chr(10)
        new = content[:pos] + inject + content[pos:]
        p.write_text(new, encoding="utf-8")
        print("test_07 isolation fixture added")
