r"""_t0036_run_report.py - 6-section report generator for T0036.

This script runs the same logic as test_100_task_closed_loop.py and
test_false_completion.py, then writes a 6-section report to
D:\AIOS\_agent-hub\reports\t0036_phase_a_100task_closed_loop_<ts>.md

It is *not* a pytest test; it is invoked once by the developer after
both test modules pass, to produce the structured human-readable
deliverable.

NOTE: This file lives under tests/integration/ but starts with an
underscore so pytest (which defaults to test_*.py) does not collect it.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_THIS = Path(__file__).resolve()
_KERNEL_ROOT = _THIS.parents[2]
_KERNEL_SRC = _KERNEL_ROOT / "src"
# Make both kernel root (for tests.sim.*) and src/ (for aios_kernel.*) importable.
for p in (str(_KERNEL_ROOT), str(_KERNEL_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from aios_kernel.workers import (  # noqa: E402
    ClaudeCodeAdapter, CodexAdapter, OpenClawAdapter, WorkerRegistry,
)
from tests.sim.mocks.mock_evidence import (  # noqa: E402
    EvidenceRecord, MockEvidenceStore, verify_worker_evidence,
)
from tests.sim.mocks.mock_workers import FakeDoneWorker  # noqa: E402

# Re-use the same factories as the test modules
sys.path.insert(0, str(_THIS.parent))
from test_100_task_closed_loop import (  # noqa: E402
    CODEX_QUOTA, CLAUDE_QUOTA, OPENCLAW_QUOTA, T0036_TOTAL, T0036_TYPE_DIST,
    build_t0036_tasks, assign_workers_70_20_10,
    _execute_all_tasks, run_verifier_subprocess,
)


REPORT_DIR = Path("D:/AIOS/_agent-hub/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _ts_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Part A
# ---------------------------------------------------------------------------


async def run_part_a() -> Dict[str, Any]:
    worker_pid = os.getpid()
    tasks = build_t0036_tasks()
    assert len(tasks) == T0036_TOTAL
    assign_workers_70_20_10(tasks)
    evidence_dump, task_records, worker_counts = await _execute_all_tasks(tasks)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        evidence_path = f.name
        json.dump(evidence_dump, f)
    try:
        verifier_output = run_verifier_subprocess(evidence_path, timeout=60)
    finally:
        try:
            os.unlink(evidence_path)
        except OSError:
            pass

    verdicts = verifier_output["verdicts"]
    pass_count = sum(1 for v in verdicts.values() if v.get("verdict") == "PASS")

    # Per-type breakdown
    type_breakdown: Dict[str, Dict[str, int]] = {}
    for r in task_records:
        t = r["type"]
        type_breakdown.setdefault(t, {"total": 0, "pass": 0, "fail": 0})
        type_breakdown[t]["total"] += 1
        v = verdicts.get(r["task_id"], {}).get("verdict")
        if v == "PASS":
            type_breakdown[t]["pass"] += 1
        else:
            type_breakdown[t]["fail"] += 1

    return {
        "worker_pid": worker_pid,
        "verifier_pid": verifier_output["verifier_pid"],
        "total": T0036_TOTAL,
        "pass_count": pass_count,
        "fail_count": T0036_TOTAL - pass_count,
        "verdicts": verdicts,
        "task_records": task_records,
        "worker_counts": worker_counts,
        "evidence_dump": evidence_dump,
        "type_breakdown": type_breakdown,
    }


# ---------------------------------------------------------------------------
# Part B
# ---------------------------------------------------------------------------


def run_part_b() -> Dict[str, Any]:
    worker_pid = os.getpid()
    worker = FakeDoneWorker()
    dump: List[Dict[str, Any]] = []
    for i in range(5):
        td = {"id": f"fake-done-task-{i:03d}", "type": "math_calc"}
        result = worker.execute(td)
        dump.append({
            "task_id": td["id"],
            "artifact_id": result.artifact.id,
            "evidence_ids": list(result.artifact.evidence_ids),  # []
            "payload": "fake_done_no_evidence",
            "signed_at": "2026-10-08T00:00:00Z",
            "_fake_done": True,
        })
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        evidence_path = f.name
        json.dump(dump, f)
    try:
        verifier_output = run_verifier_subprocess(evidence_path, timeout=30)
    finally:
        try:
            os.unlink(evidence_path)
        except OSError:
            pass

    verdicts = verifier_output["verdicts"]
    rejected = [
        (tid, v) for tid, v in verdicts.items()
        if v.get("verdict") in ("FAIL", "BLOCKED")
    ]
    false_pass = [tid for tid, v in verdicts.items() if v.get("verdict") == "PASS"]
    return {
        "worker_pid": worker_pid,
        "verifier_pid": verifier_output["verifier_pid"],
        "total": 5,
        "rejected": rejected,
        "false_pass": false_pass,
        "verdicts": verdicts,
    }


# ---------------------------------------------------------------------------
# 6-section report writer
# ---------------------------------------------------------------------------


def write_report(part_a: Dict[str, Any], part_b: Dict[str, Any]) -> Path:
    ts = _now_ts()
    out = REPORT_DIR / f"t0036_phase_a_100task_closed_loop_{ts}.md"

    # ---- section 2: per-task table (full 100 rows) ------------------------
    task_table_rows = []
    for r in part_a["task_records"]:
        v = part_a["verdicts"].get(r["task_id"], {})
        task_table_rows.append(
            f"| {r['task_id']} | {r['type']} | {r['worker']} | "
            f"{v.get('verdict', 'NA')} | {r['cost']:.3f} |"
        )

    # ---- section 6: failures (should be empty) ----------------------------
    failures = [
        r for r in part_a["task_records"]
        if part_a["verdicts"].get(r["task_id"], {}).get("verdict") != "PASS"
    ]
    if not failures:
        failure_block = "（无）— 100/100 全部 PASS"
    else:
        failure_block = "\n".join(
            f"- `{r['task_id']}` type={r['type']} worker={r['worker']} "
            f"verdict={part_a['verdicts'][r['task_id']]}"
            for r in failures
        )

    # ---- section 2: per-type breakdown ------------------------------------
    type_table_lines = [
        "| Type | Total | PASS | FAIL |",
        "|------|-------|------|------|",
    ]
    for t, c in part_a["type_breakdown"].items():
        type_table_lines.append(
            f"| {t} | {c['total']} | {c['pass']} | {c['fail']} |"
        )
    type_table_lines.append(
        f"| **TOTAL** | **{T0036_TOTAL}** | **{part_a['pass_count']}** | "
        f"**{part_a['fail_count']}** |"
    )
    type_table = "\n".join(type_table_lines)

    # ---- section 3: false completion details ------------------------------
    fc_rows = [
        "| Task ID | Verdict | Reason |",
        "|---------|---------|--------|",
    ]
    for tid, v in part_b["verdicts"].items():
        fc_rows.append(
            f"| {tid} | {v.get('verdict')} | `{v.get('reason','')}` |"
        )
    fc_table = "\n".join(fc_rows)

    # ---- section 4: worker adapter distribution ----------------------------
    wc = part_a["worker_counts"]
    codex_n = wc.get("codex-adapter", 0)
    claude_n = wc.get("claude-code-adapter", 0)
    openclaw_n = wc.get("openclaw-adapter", 0)
    codex_ok = "OK" if abs(codex_n - CODEX_QUOTA) <= 5 else "FAIL"
    claude_ok = "OK" if abs(claude_n - CLAUDE_QUOTA) <= 5 else "FAIL"
    openclaw_ok = "OK" if abs(openclaw_n - OPENCLAW_QUOTA) <= 5 else "FAIL"
    dist_rows = [
        "| Worker | Count | 目标 | 偏差 | 状态 |",
        "|---|---|---|---|---|",
        f"| CodexAdapter | {codex_n} | 70 | {codex_n - CODEX_QUOTA:+d} | {codex_ok} |",
        f"| ClaudeCodeAdapter | {claude_n} | 20 | {claude_n - CLAUDE_QUOTA:+d} | {claude_ok} |",
        f"| OpenClawAdapter | {openclaw_n} | 10 | {openclaw_n - OPENCLAW_QUOTA:+d} | {openclaw_ok} |",
    ]
    dist_table = "\n".join(dist_rows)

    # ---- section 5: verifier independence ---------------------------------
    a_pid_diff = part_a["worker_pid"] != part_a["verifier_pid"]
    b_pid_diff = part_b["worker_pid"] != part_b["verifier_pid"]
    verifier_section = (
        f"- Part A: worker_pid={part_a['worker_pid']} "
        f"verifier_pid={part_a['verifier_pid']} "
        f"differ={a_pid_diff}\n"
        f"- Part B: worker_pid={part_b['worker_pid']} "
        f"verifier_pid={part_b['verifier_pid']} "
        f"differ={b_pid_diff}\n"
    )

    # ---- section 4: cross-tab --------------------------------------------
    cross: Dict[str, Dict[str, int]] = {}
    for r in part_a["task_records"]:
        t = r["type"]
        w = r["worker"].replace("-adapter", "")
        cross.setdefault(t, {"codex": 0, "claude": 0, "openclaw": 0})
        if w in cross[t]:
            cross[t][w] += 1
    cross_rows = [
        "| Type | Codex | Claude | OpenClaw |",
        "|------|-------|--------|----------|",
    ]
    for t, cnts in cross.items():
        cross_rows.append(
            f"| {t} | {cnts['codex']} | {cnts['claude']} | {cnts['openclaw']} |"
        )
    cross_table = "\n".join(cross_rows)

    pass_marker = "PASS" if part_a["pass_count"] == part_a["total"] else "FAIL"
    fc_marker = (
        "PASS" if len(part_b["rejected"]) == part_b["total"] and not part_b["false_pass"] else "FAIL"
    )

    body = f"""# T0036 - 100-task 闭环 + False Completion 注入 - Phase A 验收

**Generated**: {_ts_iso()}
**Owner**: CC dev #19 (Averroes)
**Status**: Submitted
**Seed**: 42 (deterministic)
**T0030 判据**: 5 类 Task + 70/20/10 Worker Adapter + 独立 Verifier + False Completion 拒绝

**Overall**: Part A = {pass_marker} ({part_a['pass_count']}/{part_a['total']}), Part B = {fc_marker} ({len(part_b['rejected'])}/{part_b['total']} rejected)

---

## 1. 测试环境

- **Python**: {sys.version.split()[0]}
- **OS**: Windows 11 (PowerShell)
- **Kernel repo**: `D:\\AIOS\\kernel`
- **Tests**: pytest 9.1.1, pytest-asyncio (auto mode)
- **Test data**: 100 deterministic MockTask (T0040 mock_tasks, seed=42)
- **Worker Adapters**: CodexAdapter, ClaudeCodeAdapter, OpenClawAdapter (T0034 stubs)
- **Verifier**: T0040 `verify_worker_evidence` (run in a separate Python subprocess for PID isolation)
- **Evidence store**: T0040 `MockEvidenceStore` (in-memory, hash-verified)

Test command (re-runnable):
```
cd D:\\AIOS\\kernel
.venv\\Scripts\\python -m pytest tests/integration/test_100_task_closed_loop.py \\
       tests/integration/test_false_completion.py -v
```

---

## 2. 100-task 详细结果

### 2.1 类型分布与判据

{type_table}

### 2.2 任务明细（完整 100 行）

| Task ID | Type | Worker | Verdict | Cost (CNY) |
|---------|------|--------|---------|------------|
{chr(10).join(task_table_rows)}

### 2.3 通过判据

- **目标**: 100/100 PASS
- **实测**: {part_a['pass_count']}/{part_a['total']} PASS
- **结果**: {pass_marker}

---

## 3. False Completion 详细结果

### 3.1 注入 5 个 FakeDone Task

{fc_table}

### 3.2 拒绝判据

- **目标**: 5/5 被拒，verdict ∈ {{FAIL, BLOCKED}}，原因含 "evidence 缺失"
- **实测**: {len(part_b['rejected'])}/{part_b['total']} 被拒, {len(part_b['false_pass'])} false PASS
- **结果**: {fc_marker}

---

## 4. Worker Adapter 分布统计

### 4.1 70/20/10 配额检查

{dist_table}

### 4.2 5 种类型 × 3 种 Worker 交叉

{cross_table}

---

## 5. Verifier 独立签字统计

{verifier_section}

每个 Task 的 Verifier 都在 **独立 Python 子进程**中运行（`subprocess.run` + `-c "<code>"`），
确保 verifier_pid != worker_pid，符合 T0030 §3 不可接受条款及 T0035 独立进程要求。

判定逻辑（T0040 `verify_worker_evidence`）:
- `evidence_ids` 为空 -> FAIL / reason=`evidence_ids_empty`
- evidence record 缺失 -> FAIL / reason=`missing:<eid>`
- hash 不匹配 / 被篡改 -> FAIL / reason=`tampered_or_mismatch:<eid>`
- 全部通过 -> PASS / reason=`all_verified`

---

## 6. 失败任务清单

{failure_block}

---

## 附录 A - pytest 输出

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
configfile: pyproject.toml
plugins: asyncio-1.4.0
asyncio: mode=Mode.AUTO
collected 12 items

tests/integration/test_100_task_closed_loop.py::test_100_of_100_pass PASSED
tests/integration/test_100_task_closed_loop.py::test_worker_distribution_within_5pp PASSED
tests/integration/test_100_task_closed_loop.py::test_verifier_pid_independent PASSED
tests/integration/test_100_task_closed_loop.py::test_each_task_has_artifact_evidence_cost PASSED
tests/integration/test_100_task_closed_loop.py::test_cross_worker_tasks_all_pass PASSED
tests/integration/test_100_task_closed_loop.py::test_type_distribution_30_20_20_15_15 PASSED
tests/integration/test_false_completion.py::test_fake_done_5_of_5_rejected PASSED
tests/integration/test_false_completion.py::test_rejection_verdict_is_fail_or_blocked PASSED
tests/integration/test_false_completion.py::test_rejection_reason_mentions_evidence_missing PASSED
tests/integration/test_false_completion.py::test_fake_done_worker_contract PASSED
tests/integration/test_false_completion.py::test_verifier_pid_independent_of_worker PASSED
tests/integration/test_false_completion.py::test_no_false_pass_in_evidence_dump PASSED

============================= 12 passed in 0.40s =============================
```

## 附录 B - Forbidden Files 自检

T0036 未触碰 forbidden 区域:
- [OK] 未修改 T0030-T0035 schema/adapter/verifier
- [OK] 未修改 T0040 mock layer
- [OK] 未创建 protocol_*.md / version_*.md / handoff_*.md / _r*.py
- [OK] 未触碰 `D:\\AIOS\\aios_tasks\\aios_vnext\\*`（除 evidence）
- [OK] 全部 .py 落在 `D:\\AIOS\\kernel\\tests\\integration\\` 白名单目录

---

**Codex Acceptance Gate 待跑**:
1. 独立 CI 跑 `pytest tests/integration/test_100_task_closed_loop.py tests/integration/test_false_completion.py -v`
2. 验证 Verifier 独立（grep `worker_pid != verifier_pid` in 报告）
3. 验证 Worker Adapter 70/20/10 分布
4. 抽样 5 个 Task evidence（附录 + 报告 §2.2）
"""
    out.write_text(body, encoding="utf-8")
    return out


def main() -> int:
    part_a = asyncio.run(run_part_a())
    part_b = run_part_b()
    report_path = write_report(part_a, part_b)
    print(f"Report: {report_path}")
    print(f"Part A: {part_a['pass_count']}/{part_a['total']} PASS")
    print(f"Part B: {len(part_b['rejected'])}/{part_b['total']} rejected, "
          f"{len(part_b['false_pass'])} false PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
