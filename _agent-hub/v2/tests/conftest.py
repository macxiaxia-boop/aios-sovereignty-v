# v2/tests/conftest.py — common test setup.
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Use a temp dir as v2 root so tests are isolated.
TEST_ROOT = Path(tempfile.mkdtemp(prefix="aiosv2_test_")).resolve()
os.environ["AIOS_V2_ROOT"] = str(TEST_ROOT)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Init dirs
from src.paths import ensure_dirs  # noqa: E402

ensure_dirs()

# pytest is OPTIONAL — only needed when running `pytest tests/`.
# The bundled driver (run_all_tests.py) does NOT need it.
try:
    import pytest  # noqa: E402, F401
except ImportError:
    # Minimal polyfill: only `pytest.raises` is used by the test suite.
    class _RaisesCtx:
        def __init__(self, exc):
            self.exc = exc

        def __enter__(self):
            return self

        def __exit__(self, et, ev, tb):
            if et is None:
                raise AssertionError(
                    f"Expected exception of type {self.exc.__name__} but none was raised"
                )
            if not issubclass(et, self.exc):
                return False  # propagate unexpected exception
            return True  # suppress the expected one

    class _PytestShim:
        @staticmethod
        def raises(exc):
            return _RaisesCtx(exc)

    pytest = _PytestShim()  # type: ignore