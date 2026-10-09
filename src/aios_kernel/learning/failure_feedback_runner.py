r"""failure_feedback_runner.py - CLI entry for FailureFeedbackService (Phase G G001).

读 failure traces (默认 JSONL 文件) -> FailurePatternMerger cluster
-> FailureFeedbackService.apply_clusters_to_active_goals

设计原则:
- 不改 verifier/deterministic.py / v2 consumer / GoalGuard
- trace source 默认是 JSONL (每行一个 JSON dict, 字段: id, error_message,
  error_type, context, timestamp); production 改 JSONL -> 数据库 reader
- 与 Scheduled Task 集成: run_failure_feedback.cmd 调用本模块

Card: D:\AIOS\aios_tasks\aios_vnext\cards\G001_failure_feedback.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Protocol, runtime_checkable

from aios_kernel.learning.clustering import FailureCluster, FailurePatternMerger, FailureTrace
from aios_kernel.learning.failure_feedback import (
    DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK,
    FailureFeedbackService,
)

log = logging.getLogger(__name__)


# ----- trace source protocol ----------------------------------------------


@runtime_checkable
class FailureTraceSource(Protocol):
    """任何能 yield FailureTrace 的对象 (file / db / in-memory list) 都可以."""

    def read(self) -> Iterable[FailureTrace]:
        ...


class JsonlFileTraceSource:
    """从 JSONL 文件读 FailureTrace. 每行一个 JSON dict."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read(self) -> list[FailureTrace]:
        if not self.path.exists():
            log.warning("failure_feedback_runner: trace file %s not found, returning []", self.path)
            return []
        traces: list[FailureTrace] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line_no, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw or raw.startswith("#"):
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as e:
                    log.warning("failure_feedback_runner: bad JSON at line %d: %s", line_no, e)
                    continue
                try:
                    traces.append(
                        FailureTrace(
                            id=str(obj["id"]),
                            error_message=str(obj.get("error_message", "")),
                            error_type=str(obj.get("error_type", "")),
                            context=dict(obj.get("context") or {}),
                            timestamp=str(obj.get("timestamp") or ""),
                        )
                    )
                except (KeyError, TypeError) as e:
                    log.warning("failure_feedback_runner: bad record at line %d: %s", line_no, e)
        return traces


class InMemoryTraceSource:
    """测试 / 内置 fixture 用."""

    def __init__(self, traces: Iterable[FailureTrace]):
        self._traces = list(traces)

    def read(self) -> list[FailureTrace]:
        return list(self._traces)


# ----- main --------------------------------------------------------------


def _default_trace_path() -> Path:
    """默认 trace 文件路径. 可被 env var AIOS_FAILURE_TRACE_PATH 覆盖."""
    override = os.environ.get("AIOS_FAILURE_TRACE_PATH")
    if override:
        return Path(override)
    # 默认: kernel/state/failures/YYYY-MM-DD.jsonl (相对当前 cwd)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Path.cwd() / "state" / "failures" / f"{today}.jsonl"


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="failure_feedback_runner",
        description="Apply FailurePatternMerger clusters to active Goals (Phase G G001)",
    )
    p.add_argument(
        "--min-occurrence",
        type=int,
        default=DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK,
        help=f"Min cluster occurrence to write back (default: {DEFAULT_MIN_OCCURRENCE_FOR_FEEDBACK})",
    )
    p.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Scheduled interval in seconds (informational; not used in single-run mode). Default: 900 (15 min)",
    )
    p.add_argument(
        "--trace-path",
        type=str,
        default=None,
        help="Path to JSONL failure trace file. Defaults to AIOS_FAILURE_TRACE_PATH or state/failures/YYYY-MM-DD.jsonl",
    )
    p.add_argument(
        "--once",
        action="store_true",
        default=True,
        help="Run once and exit (default behavior; --interval is for Scheduled Task reference).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Compute clusters and show what would be applied; do not write to DB.",
    )
    p.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p


def _collect_traces(source: FailureTraceSource) -> list[FailureTrace]:
    return list(source.read())


def _cluster_traces(traces: list[FailureTrace]) -> list[FailureCluster]:
    merger = FailurePatternMerger()
    return merger.merge(traces)


def _summary(results: dict[str, list[str]], clusters: list[FailureCluster]) -> dict:
    total_added = sum(len(v) for v in results.values())
    return {
        "cluster_count": len(clusters),
        "active_goal_count": len(results),
        "total_modes_added": total_added,
        "per_goal": {gid: len(added) for gid, added in results.items()},
    }


async def run_once(
    source: FailureTraceSource,
    min_occurrence: int,
    dry_run: bool = False,
) -> dict:
    """单次执行: collect -> cluster -> apply.

    Returns:
        summary dict (cluster_count, active_goal_count, total_modes_added, per_goal)
    """
    traces = _collect_traces(source)
    log.info("failure_feedback_runner: collected %d traces", len(traces))

    clusters = _cluster_traces(traces)
    log.info(
        "failure_feedback_runner: %d clusters (occurrence >= %d: %d)",
        len(clusters),
        min_occurrence,
        sum(1 for c in clusters if c.occurrence_count >= min_occurrence),
    )

    if dry_run:
        return _summary({}, clusters)

    # real run: 接 SqlAlchemyRepository (InMemoryRepository 仅在测试)
    from aios_kernel.domain.services.repository import (
        make_engine,
        make_session_factory,
        session_scope,
    )
    from aios_kernel.persistence import SqlAlchemyRepository

    engine = make_engine()
    factory = make_session_factory(engine)
    try:
        async with session_scope(factory) as session:
            repo = SqlAlchemyRepository(session)
            service = FailureFeedbackService(repo, repo)
            results = await service.apply_clusters_to_active_goals(clusters, min_occurrence)
    finally:
        await engine.dispose()

    return _summary(results, clusters)


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    trace_path = Path(args.trace_path) if args.trace_path else _default_trace_path()
    source: FailureTraceSource = JsonlFileTraceSource(trace_path)
    log.info("failure_feedback_runner: trace source = %s", trace_path)

    summary = asyncio.run(
        run_once(source, min_occurrence=args.min_occurrence, dry_run=args.dry_run)
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
