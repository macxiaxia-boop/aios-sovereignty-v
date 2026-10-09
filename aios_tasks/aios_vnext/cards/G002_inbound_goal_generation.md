---
id: G002
title: v2 inbound 通用 GoalContract 生成 + GoalGuard 校验循环
owner: CC
priority: P0
track: 7 — VNext Phase G (Learning Closure)
preconditions: [G000, F002, F005]
estimated_minutes: 120
depends_on: [G000, F002, F005]
blocks: [G004]
status: Pending
created: 2026-10-09
codex_supervisor_signoff_required: true
---

## Scope (要做)

把"v2 inbound envelope → 自动生成 GoalContract → GoalGuard 校验 → 分派 worker"做成通用流程（不是 hardcode 单一 Goal）。

### 1. 必建/改文件（白名单内）

**`D:\AIOS\_agent-hub\v2\src\inbound_goal_generation.py`** — 新建：

```python
"""inbound_goal_generation.py — v2 inbound envelope → GoalContract 生成 (Phase G G002).

通用循环:
  1. v2 inbound envelope (text payload)
  2. IntentParser → 解析成 GoalContract 12 字段
  3. cache 到 _agent-hub/v2/state/generated_goals/
  4. GoalGuard.validate(contract) → risk_block / pass
  5. pass → continue dispatch; risk_block → write risk envelope

不 hardcode 单一 Goal, 接受任何 inbound envelope.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios_kernel.intent.parser import IntentParser
from aios_kernel.intent.llm_adapter import NullLLMAdapter
from aios_kernel.domain.goal import (
    Goal, GoalStatus, Constraint, EnvSnapshot, FailureMode,
    PermissionScope, EvidenceRequest, Tradeoff, OpType,
)
from aios_kernel.governance.goal_guard import GoalGuard, GuardVerdict

GENERATED_GOALS_DIR = Path("D:/AIOS/_agent-hub/v2/state/generated_goals")


def envelope_to_goal_payload(envelope: dict) -> dict:
    """从 envelope payload 提取 goal-relevant fields. 返回 dict 用于 IntentParser."""
    if not isinstance(envelope, dict):
        return {}
    payload = envelope.get("payload") or {}
    if not isinstance(payload, dict):
        return {}
    # 多种来源: payload.goal / payload.title+text / payload 直接是 goal dict
    if "goal" in payload and isinstance(payload["goal"], dict):
        return payload["goal"]
    if "title" in payload:
        return dict(payload)
    return {}


def generate_goal_from_envelope(
    envelope: dict,
    parser: IntentParser | None = None,
) -> Goal:
    """Generic inbound envelope → Goal instance.
    
    不 hardcode 任何 Goal 字段 — 全部从 envelope + IntentParser 推断。
    """
    parser = parser or IntentParser(llm_adapter=NullLLMAdapter())
    raw = envelope_to_goal_payload(envelope)
    user_text = raw.get("text") or raw.get("description") or raw.get("title") or ""
    
    # 用 IntentParser 推断 GoalContract 12 字段
    parsed = parser.parse(user_text)
    
    # 构造 Goal instance
    goal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    goal = Goal(
        id=goal_id,
        title=parsed.get("title") or raw.get("title") or "untitled",
        description=parsed.get("description") or user_text or "",
        success_criteria=parsed.get("success_criteria") or "live",
        budget=float(raw.get("budget", 0.0)),
        deadline=None,
        owner=raw.get("owner") or envelope.get("sender") or "codex",
        status=GoalStatus.PENDING,
        tags=list(raw.get("tags", [])),
        plan_ids=[],
        inferred_intent=parsed.get("inferred_intent"),
        preserve_capabilities=list(raw.get("preserve_capabilities", [
            "verifier/deterministic.py",
            "v2 consumer main loop",
            "AGENTS.md SSOT",
        ])),
        known_constraints=[
            Constraint(type="scope", value="inbound envelope", rationale="from v2 channel"),
        ],
        environment_context=EnvSnapshot(
            cwd="D:/AIOS",
            os="Windows",
            envelope_id=envelope.get("id", ""),
            available_tools=[],
        ),
        failure_modes=[],
        permission_scope=PermissionScope(
            allowed_paths=[],
            allowed_ops=["read", "write", "execute"],
            max_budget=float(raw.get("budget", 0.0)),
            max_duration_sec=300,
            requires_approval=["delete", "network"],
        ),
        missing_evidence=[],
        approved_tradeoffs=[],
        autonomous_scope=[
            OpType(domain="file", action="read"),
            OpType(domain="file", action="write", target="D:/AIOS/_agent-hub/"),
        ],
        requires_authorization=[
            OpType(domain="file", action="delete"),
            OpType(domain="file", action="modify", target="D:/AIOS/_agent-hub/AGENTS.md"),
        ],
    )
    return goal


def cache_goal_to_disk(goal: Goal, root: Path | None = None) -> Path:
    """持久化 Goal 到 disk 备审计. Returns 写入 path."""
    root = root or GENERATED_GOALS_DIR
    root.mkdir(parents=True, exist_ok=True)
    goal_dict = goal.model_dump(mode="json")
    goal_dict["status"] = goal.status.value
    fname = root / f"{goal.id}.json"
    fname.write_text(json.dumps(goal_dict, indent=2, ensure_ascii=False), encoding="utf-8")
    return fname


def validate_with_goal_guard(goal: Goal) -> tuple[bool, dict | None]:
    """GoalGuard 校验. 返回 (allowed, risk_envelope_or_None)."""
    guard = GoalGuard()
    report = guard.validate(goal)
    if report.verdict == GuardVerdict.PASS:
        return True, None
    # construct risk envelope (与 Phase F005 一致)
    risk = {
        "type": "goal_guard_risk",
        "verdict": report.verdict.value,
        "passed_checks": report.passed_checks,
        "failed_checks": report.failed_checks,
        "goal_id": goal.id,
    }
    return False, risk


def process_inbound_envelope(
    envelope: dict,
    parser: IntentParser | None = None,
    root: Path | None = None,
) -> tuple[Goal, bool, dict | None, Path | None]:
    """完整 inbound → GoalContract → GoalGuard → cache → return
    
    Returns: (goal, allowed, risk_envelope_or_None, cache_path_or_None)
    """
    goal = generate_goal_from_envelope(envelope, parser)
    cache_path = cache_goal_to_disk(goal, root)
    allowed, risk = validate_with_goal_guard(goal)
    if allowed:
        goal.transition_to(GoalStatus.ACTIVE)
    return goal, allowed, risk, cache_path


__all__ = [
    "envelope_to_goal_payload",
    "generate_goal_from_envelope",
    "cache_goal_to_disk",
    "validate_with_goal_guard",
    "process_inbound_envelope",
    "GENERATED_GOALS_DIR",
]
```

**`D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py`** — 最小修改：在 `guard_dispatch()` 开头插入 `process_inbound_envelope()` 调用生成GoalContract 并 cache：

```python
# Phase G G002: Inbound → GoalContract (在 head)
from inbound_goal_generation import process_inbound_envelope

def guard_dispatch(envelope, v2_root=None):
    # G002: 生成 GoalContract (通用循环)
    try:
        goal, allowed_gen, risk_gen, cache_path = process_inbound_envelope(envelope)
        if not allowed_gen:
            # GoalGuard 拒绝, 写 risk envelope
            return False, risk_gen
    except Exception as exc:
        if os.environ.get("AIOS_GOAL_GUARD_DEBUG") == "1":
            print(f"[goal_guard_hook] inbound_goal_generation failed: {exc}", flush=True)
        # fail-open: continue to existing logic

    # 既有 logic 继续 (F005 + Phase-2)
    ...
```

**`D:\AIOS\_agent-hub\v2\tests\test_inbound_goal_generation.py`** — 15+ case

### 2. 单元测试 (15+ case)

```python
def test_envelope_to_goal_payload_with_goal_field()
def test_envelope_to_goal_payload_with_title_field()
def test_envelope_to_goal_payload_empty_envelope()
def test_generate_goal_from_envelope_basic()
def test_generate_goal_from_envelope_uses_intent_parser()
def test_generate_goal_from_envelope_preserves_capabilities_default()
def test_generate_goal_from_envelope_permission_scope_minimal()
def test_cache_goal_to_disk_creates_file()
def test_cache_goal_to_disk_idempotent_overwrites()
def test_cache_goal_to_disk_includes_status()
def test_validate_with_goal_guard_pass_complete()
def test_validate_with_goal_guard_block_incomplete()
def test_validate_with_goal_guard_block_permission_overrun()
def test_process_inbound_envelope_full_pipeline_pass()
def test_process_inbound_envelope_full_pipeline_block()
def test_process_inbound_envelope_caches_to_disk()
def test_inbound_to_dispatch_hook_integration()
def test_generic_envelope_no_hardcode()
def test_intent_parser_inferred_intent_field_used()
def test_intent_parser_known_constraints_extracted()
```

### 3. 关键设计
- 不 hardcode 任何 Goal 字段 — 全部从 envelope + IntentParser
- 用 IntentParser 推断 (inferred_intent, known_constraints 等)
- 写到 disk 备审计 (`v2/state/generated_goals/{goal_id}.json`)
- GoalGuard 自动校验
- 入点: `goal_guard_hook.guard_dispatch()` 开头

## Out-of-scope (不要做)

- ❌ 不重写 IntentParser (F002 已有)
- ❌ 不重写 GoalGuard (F005 已有)
- ❌ 不改 v2 consumer / v2_consumer.py 主循环
- ❌ 不实现 cross-agent knowledge (G003 才做)
- ❌ 不实现 failure feedback 反哺 (G001 才做)
- ❌ 不创建 `_v6_*.py` / `_r*.py` / `protocol_*.md` 等 forbidden pattern

## Inputs (必须先读)

1. `D:\AIOS\kernel\src\aios_kernel\intent\parser.py` — IntentParser
2. `D:\AIOS\kernel\src\aios_kernel\governance\goal_guard.py` — GoalGuard
3. `D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py` — F005 接入点
4. `D:\AIOS\aios_tasks\aios_vnext\cards\F002_intent_parser.md`
5. `D:\AIOS\aios_tasks\aios_vnext\cards\F005_goal_guard_hook.md`
6. `D:\AIOS\aios_tasks\aios_vnext\cards\G000_phase_g_acceptance_spec.md`

## Outputs (必须产出)

1. `D:\AIOS\aios_tasks\aios_vnext\evidence\G002__<ts>.md` — 必含 preflight
3. `D:\AIOS\_agent-hub\v2\src\inbound_goal_generation.py` — process_inbound_envelope
4. `D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py` — diff ≤ 10 行
5. `D:\AIOS\_agent-hub\v2\tests\test_inbound_goal_generation.py` — 15+ case

## Evidence Requirements

- [ ] process_inbound_envelope() 可 import + 调用
- [ ] 15+ case 全 PASS
- [ ] Generic envelope → GoalContract 不 hardcode
- [ ] cache_goal_to_disk 实际写文件
- [ ] GoalGuard validate() 在 pipeline 内调用
- [ ] goal_guard_hook diff ≤ 10 行
- [ ] preflight = 0 issues
- [ ] 现有 baseline 不退化

## Exit Criteria

1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex
3. **不自封 Verified**

## Rollback

1. 恢复 `goal_guard_hook.py` 到 git HEAD
2. 删除 `inbound_goal_generation.py`
3. 删除 `test_inbound_goal_generation.py`
4. `git reset --hard HEAD~1`（如有 commit）

## Time Budget

120 分钟

## Codex Acceptance Gate

Codex 独立验证：
1. `pytest _agent-hub/v2/tests/test_inbound_goal_generation.py -v` 15+ PASS
2. 手动测试 1 个 generic envelope → cache 文件
4. `git diff _agent-hub/v2/src/goal_guard_hook.py` 行数 ≤ 10
5. `pytest _agent-hub/v2/tests/ -v` 既有 baseline 不退化
6. `pytest kernel/tests/unit -v` 全套仍 PASS
7. preflight v4 = 0 issues

通过 → status=Verified