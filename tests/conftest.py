"""conftest.py - top-level pytest config for AIOS kernel."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# ensure src/ is on sys.path for `import aios_kernel` lookups.
_SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(_SRC))

# Bare-name alias: tests do `from goal_guard_hook import ...`.
_STUB = _SRC / "aios_kernel" / "governance" / "goal_guard_hook.py"
if _STUB.exists() and "goal_guard_hook" not in sys.modules:
    spec = importlib.util.spec_from_file_location("goal_guard_hook", str(_STUB))
    _mod = importlib.util.module_from_spec(spec)
    sys.modules["goal_guard_hook"] = _mod
    spec.loader.exec_module(_mod)
