"""AIOS Kernel CLI entry point (placeholder).

Real commands are added in later cards (T0032+). For now we only expose
``--version`` so the kernel package is operationally usable post-install.
"""
from __future__ import annotations

import argparse

from aios_kernel import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aios-kernel",
        description="AIOS Kernel CLI (VNext Phase A scaffold).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"aios-kernel {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    # parse_args handles --version (raises SystemExit → caller sees it)
    # and consumes any future subcommands.
    parser.parse_args(argv)
    # No subcommand given → print help and exit 0.
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
