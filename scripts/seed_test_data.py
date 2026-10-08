"""Seed test data into the AIOS Kernel database (T0031 placeholder).

The real seed routine arrives in T0032 once the Goal/State/Task/Plan schemas
are wired into ``aios_kernel.persistence``. For now this script only verifies
that the ``aios_kernel`` package is importable end-to-end.
"""
from __future__ import annotations

import sys

from aios_kernel import __version__


def main() -> int:
    print(f"aios-kernel {__version__} — seed_test_data stub")
    print("(no-op; T0032 will introduce real seed data)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
