"""AIOS Kernel CLI entry point.

Commands (R1503-001 enhanced):
  - --version
  - scheduler            run the AIOSScheduler (foreground, blocks)
  - scheduler status     print metrics snapshot
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os

from aios_kernel import __version__
from aios_kernel.scheduler import AIOSScheduler, SchedulerConfig
from aios_kernel.workers.claude_code_adapter import ClaudeCodeAdapter
from aios_kernel.workers.codex_adapter import CodexAdapter
from aios_kernel.workers.hermes_adapter import HermesAdapter
from aios_kernel.workers.openclaw_adapter import OpenClawAdapter
from aios_kernel.workers.registry import WorkerRegistry

log = logging.getLogger("aios_kernel.cli")


def build_default_registry() -> WorkerRegistry:
    """Wire up the 4-Agent Worker Adapter team (R1503 §2)."""
    registry = WorkerRegistry()
    registry.register(ClaudeCodeAdapter())
    registry.register(CodexAdapter())
    registry.register(OpenClawAdapter())
    registry.register(HermesAdapter())
    # The existing specialized CloudTech bridge is deliberately opt-in:
    # without an explicit service URL there must be no mock/silent fallback.
    if os.environ.get("CLOUDTECH_V4_BASE_URL"):
        from aios_kernel.workers.cloudtech_v4_adapter import CloudTechV4Adapter

        registry.register(CloudTechV4Adapter())
    return registry


async def _cmd_scheduler_status(_args: argparse.Namespace) -> int:
    registry = build_default_registry()
    scheduler = AIOSScheduler(registry=registry, config=SchedulerConfig(max_concurrent=0))
    print("scheduler.metrics (idle, no dispatcher started):")
    print(scheduler.metrics())
    return 0


async def _cmd_scheduler_run(_args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    registry = build_default_registry()
    scheduler = AIOSScheduler(registry=registry)
    await scheduler.start()
    log.info("aios-kernel scheduler started. Ctrl-C to stop.")
    try:
        while True:
            await asyncio.sleep(60)
            snap = scheduler.metrics()
            log.info("scheduler.metrics: %s", snap)
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("shutting down scheduler...")
        await scheduler.stop()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aios-kernel",
        description="AIOS Kernel CLI (VNext Phase A scaffold + R1503 scheduler).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"aios-kernel {__version__}",
    )
    sub = parser.add_subparsers(dest="command")

    # scheduler subcommand
    p_sched = sub.add_parser("scheduler", help="Run the AIOSScheduler.")
    p_sched.add_argument(
        "action",
        choices=["run", "status"],
        nargs="?",
        default="run",
        help="run = foreground scheduler, status = print metrics snapshot",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "scheduler":
        if args.action == "status":
            return asyncio.run(_cmd_scheduler_status(args))
        # default: run
        return asyncio.run(_cmd_scheduler_run(args))

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
