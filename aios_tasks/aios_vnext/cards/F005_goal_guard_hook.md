---
id: F005
title: GoalGuard Hook — v2 consumer 派发前 GoalContract 校验
owner: CC
priority: P0
track: 6 — VNext Phase F (Cognitive Governance)
preconditions: [F001, F002, F003, F004]
estimated_minutes: 45
depends_on: [F001, F002, F003, F004]
blocks: []
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

在 v2 consumer (`v2_consumer.py::dispatch_envelope`) 派发前插入 GoalGuard Hook，校验每个 envelope 的 GoalContract 完整性。

### 1. 必建/改文件（白名单内）

**`D:\AIOS\kernel\src\aios_kernel\governance\__init__.py`** — 空

**`D:\AIOS\kernel\src\aios_kernel\governance\goal_guard.py`** — 新建：

```python
"""goal_guard.py — GoalContract validation guard (F005).

v2 consumer 在 dispatch envelope 前调用 GoalGuard.validate(contract)。
"""
from __future__ import annotations

from enum import Enum
from typing import ClassVar

from aios_kernel.domain.goal import Goal, GoalStatus


class GuardVerdict(str, Enum):
    """Guard 校验结果"""
    PASS = "pass"           # 通过 dispatch
    RISK_BLOCK = "risk_block"  # 不通过，写 risk audit envelope
    FATAL = "fatal"          # 致命错误，envelope 隔离


class GuardReport:
    """校验报告"""
    verdict: GuardVerdict
    passed_checks: list[str]
    failed_checks: list[str]
    risk_envelope: dict | None = None  # 当 verdict=RISK_BLOCK
    
    def to_dict(self):
        return {
            "verdict": self.verdict.value,
            "passed": self.passed_checks,
            "failed": self.failed_checks,
            "risk_envelope": self.risk_envelope,
        }


class GoalGuard:
    """GoalContract 完整 + 越权 + 失败陷阱检测"""
    
    REQUIRED_FIELDS: ClassVar[list[str]] = [
        "title", "success_criteria", "budget", "owner", "status",
        "permission_scope", "failure_modes", "missing_evidence",
        "autonomous_scope", "requires_authorization",
    ]
    
    def validate(self, goal: Goal) -> GuardReport:
        """主入口"""
        passed, failed = [], []
        
        # Check 1: 必填字段完整性
        missing = self._check_required(goal)
        if not missing:
            passed.append("required_fields_complete")
        else:
            failed.append(f"required_fields_missing: {missing}")
        
        # Check 2: 失败陷阱（surface success trap）非空
        if goal.failure_modes:
            passed.append("failure_modes_present")
        else:
            failed.append("failure_modes_empty (surface success trap risk)")
        
        # Check 3: 权限范围越权检测
        overrun = self._check_permission_overrun(goal)
        if not overrun:
            passed.append("permission_scope_in_bounds")
        else:
            failed.append(f"permission_overrun: {overrun}")
        
        # Check 4: autonomous_scope vs requires_authorization 不重叠
        overlap = self._check_scope_overlap(goal)
        if not overlap:
            passed.append("autonomous_vs_authorization_disjoint")
        else:
            failed.append(f"scope_overlap: {overlap}")
        
        # Check 5: 缺失证据非空 → 必须有采集计划
        if goal.missing_evidence:
            has_plan = any(em.required for em in goal.missing_evidence)
            if has_plan:
                passed.append("missing_evidence_has_collection_plan")
            else:
                failed.append("missing_evidence_no_collection_plan")
        else:
            passed.append("missing_evidence_empty_ok")
        
        # 决定 verdict
        if not failed:
            return GuardReport(GuardVerdict.PASS, passed, [])
        elif any("overrun" in f for f in failed):
            return GuardReport(GuardVerdict.FATAL, passed, failed)
        else:
            return GuardReport(GuardVerdict.RISK_BLOCK, passed, failed)
    
    def _check_required(self, goal: Goal) -> list[str]:
        missing = []
        for field in self.REQUIRED_FIELDS:
            v = getattr(goal, field, None)
            if v is None or (isinstance(v, (list, str)) and len(v) == 0):
                missing.append(field)
        return missing
    
    def _check_permission_overrun(self, goal: Goal) -> list[str]:
        if not goal.permission_scope:
            return ["permission_scope_missing"]
        issues = []
        # 禁止触碰 verifier/deterministic.py
        forbidden_paths = ["D:/AIOS/kernel/src/aios_kernel/verifier/", 
                          "D:/AIOS/_agent-hub/AGENTS.md"]
        for allowed in goal.permission_scope.allowed_paths:
            for fp in forbidden_paths:
                if allowed.startswith(fp):
                    issues.append(f"forbidden_path_access: {allowed}")
        return issues
    
    def _check_scope_overlap(self, goal: Goal) -> list[str]:
        auto_set = {(op.domain, op.action) for op in goal.autonomous_scope}
        auth_set = {(op.domain, op.action) for op in goal.requires_authorization}
        overlap = auto_set & auth_set
        return [{"domain": d, "action": a} for (d, a) in overlap]


def make_risk_envelope(goal: Goal, report: GuardReport, original_envelope: dict) -> dict:
    """生成 risk audit envelope（verdict=RISK_BLOCK 时写回 v2 messages/risk/）"""
    return {
        "type": "goal_guard_risk",
        "goal_id": goal.id,
        "verdict": report.verdict.value,
        "failed_checks": report.failed_checks,
        "passed_checks": report.passed_checks,
        "original_envelope_id": original_envelope.get("id"),
        "original_envelope_type": original_envelope.get("type"),
        "actor": "goal_guard",
        "timestamp": original_envelope.get("received_at"),  # 用原 envelope 时间
    }
```

### 2. 接入 v2 consumer（**只增不改**）

**`D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py`** — 新建接入文件：

```python
"""goal_guard_hook.py — v2 consumer dispatch_envelope 前的 Guard hook (F005).

不动 v2_consumer.py 主循环，只在 dispatch_envelope 调用前执行 GoalGuard.validate。
失败时把 envelope 转入 risk/ 目录，不 dispatch 给 worker。
"""
from __future__ import annotations

import json
from pathlib import Path

from aios_kernel.governance.goal_guard import GoalGuard, GuardVerdict, make_risk_envelope
from aios_kernel.domain.goal import Goal


def guard_dispatch(envelope: dict, v2_root: Path, goal_loader=None) -> tuple[bool, dict | None]:
    """
    在 v2 consumer dispatch 前调用。
    返回 (dispatch_allowed, risk_envelope_or_None)
    """
    goal_id = envelope.get("goal_id")
    if not goal_id:
        # 无 goal_id 的 envelope（系统内部消息）放行
        return True, None
    
    # 加载 Goal
    if goal_loader is None:
        # 默认：从 aios_kernel 加载
        from aios_kernel.persistence.repository import Repository
        # 这里需要真实 DB session，留 hook
        return True, None
    
    goal = goal_loader(goal_id)
    if goal is None:
        # Goal 不存在 = 系统内部消息，放行
        return True, None
    
    guard = GoalGuard()
    report = guard.validate(goal)
    
    if report.verdict == GuardVerdict.PASS:
        return True, None
    elif report.verdict == GuardVerdict.RISK_BLOCK:
        risk_env = make_risk_envelope(goal, report, envelope)
        return False, risk_env
    else:  # FATAL
        # 致命：直接丢 envelope，写 risk envelope 提示人工
        risk_env = make_risk_envelope(goal, report, envelope)
        return False, risk_env


def write_risk_envelope(v2_root: Path, risk_envelope: dict):
    """写 risk envelope 到 v2/messages/risk/"""
    risk_dir = v2_root / "messages" / "risk"
    risk_dir.mkdir(parents=True, exist_ok=True)
    fname = risk_dir / f"{risk_envelope['goal_id']}_{int(__import__('time').time())}.json"
    fname.write_text(json.dumps(risk_envelope, indent=2, ensure_ascii=False), encoding="utf-8")
    return fname
```

### 3. v2_consumer 接入点（**最小改动**）

**`D:\AIOS\_agent-hub\v2\src\v2_consumer.py`** — 在 `dispatch_envelope` 函数**开头**插入：

```python
# F005 Hook (Phase F)
from goal_guard_hook import guard_dispatch, write_risk_envelope
v2_root_path = Path(__file__).parent.parent  # _agent-hub/v2/

def dispatch_envelope(env):  # 既有函数签名不变
    # F005: GoalGuard check
    allowed, risk_env = guard_dispatch(env, v2_root_path)
    if not allowed:
        write_risk_envelope(v2_root_path, risk_env)
        log.warning("goal_guard_blocked envelope_id=%s verdict=%s", env.get("id"), risk_env["verdict"])
        return  # 不 dispatch
    # 既有 dispatch 逻辑（不动）
    ...
```

**⚠️ 注意**：只增 1 个 import + 1 个 guard call + 1 个 early return。**不重写 dispatch 主体**。

### 4. 单元测试（15+ case）

**`D:\AIOS\kernel\tests\unit\test_goal_guard.py`**：

```python
# Construction
def test_goal_guard_init_no_args()
def test_goal_guard_required_fields_list_10()
# PASS case
def test_validate_complete_goal_returns_pass()
def test_validate_minimal_goal_passes_when_all_required()
# Missing fields
def test_validate_missing_title_returns_risk_block()
def test_validate_missing_permission_scope_returns_risk_block()
def test_validate_missing_failure_modes_returns_risk_block()
def test_validate_missing_autonomous_scope_returns_risk_block()
def test_validate_missing_requires_authorization_returns_risk_block()
# Failure modes
def test_failure_modes_empty_returns_risk_block()
def test_failure_modes_present_passes()
# Permission overrun
def test_permission_scope_overrun_verifier_returns_fatal()
def test_permission_scope_overrun_agents_md_returns_fatal()
def test_permission_scope_safe_passes()
# Scope overlap
def test_autonomous_and_authorization_overlap_returns_risk_block()
def test_autonomous_and_authorization_disjoint_passes()
# Risk envelope
def test_make_risk_envelope_format()
def test_write_risk_envelope_creates_file()
# Integration
def test_guard_dispatch_with_no_goal_id_passes()
def test_guard_dispatch_with_missing_goal_passes()
def test_guard_dispatch_with_complete_goal_passes()
def test_guard_dispatch_with_incomplete_goal_blocks()
```

### 5. 集成测试

**`D:\AIOS\_agent-hub\v2\tests\test_goal_guard_hook.py`**：

```python
def test_v2_consumer_with_goal_guard_blocks_incomplete():
    """v2 consumer 在 GoalGuard 阻止 incomplete envelope 时不 dispatch"""
    # 1. 准备一个 incomplete Goal (缺 failure_modes)
    # 2. 写 envelope 到 v2/inbox
    # 3. 启动 consumer 一帧
    # 4. 验证：worker 未收到 dispatch；risk/ 目录有 envelope

def test_v2_consumer_with_complete_goal_dispatches():
    """完整 Goal 时正常 dispatch"""
    # 1. 准备完整 Goal (12 字段全)
    # 2. 写 envelope 到 v2/inbox
    # 3. consumer 派单
    # 4. 验证：worker 收到 task
```

## Out-of-scope (不要做)

- ❌ 不重写 v2 consumer 主循环（只增 1 个 import + 1 个 guard call + 1 个 early return）
- ❌ 不重写 verifier/deterministic.py
- ❌ 不重写 Goal 模型（F001 已扩）
- ❌ 不重写 DecisionAuditORM（F003 已建）
- ❌ 不改 GoalGuard 失败时的 fallback 策略（v2 consumer 已有的 fallback 仍生效）
- ❌ 不创建 `_v6_*.py` / `_r*.py` / `protocol_*.md` 等 forbidden

## Inputs (必须先读)

1. `D:\AIOS\kernel\src\aios_kernel\domain\goal.py` — Goal schema（F001 已扩 12 字段）
2. `D:\AIOS\kernel\src\aios_kernel\governance\` — 不存在，要新建
3. `D:\AIOS\_agent-hub\v2\src\v2_consumer.py` — 37.4 KB 主循环
4. `D:\AIOS\_agent-hub\v2\src\envelope.py` — envelope schema
5. `D:\AIOS\aios_tasks\aios_vnext\cards\F001_goal_contract_12_fields.md`
6. `D:\AIOS\aios_tasks\aios_vnext\cards\F002_intent_parser.md`
7. `D:\AIOS\aios_tasks\aios_vnext\cards\F003_decision_audit_log.md`
8. `D:\AIOS\aios_tasks\aios_vnext\cards\F004_failure_pattern_merger.md`

## Outputs (必须产出)

1. `D:\AIOS\aios_tasks\aios_vnext\evidence\F005__<ts>.md` — 必含 preflight 附件
2. `D:\AIOS\kernel\src\aios_kernel\governance\__init__.py`
3. `D:\AIOS\kernel\src\aios_kernel\governance\goal_guard.py`
4. `D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py`
5. `D:\AIOS\_agent-hub\v2\src\v2_consumer.py` — **只增 1 个 import + 1 个 guard call + 1 个 early return**（diff ≤ 10 行）
6. `D:\AIOS\kernel\tests\unit\test_goal_guard.py` — 15+ case
7. `D:\AIOS\_agent-hub\v2\tests\test_goal_guard_hook.py` — 集成测试

## Evidence Requirements

- [ ] GoalGuard.validate() 返回 GuardVerdict.PASS / RISK_BLOCK / FATAL
- [ ] 5 类检查（required/failure_modes/permission/scope_overlap/missing_evidence_plan）全 PASS
- [ ] `pytest tests/unit/test_goal_guard.py -v` 15+ case PASS
- [ ] `pytest _agent-hub/v2/tests/test_goal_guard_hook.py -v` 集成测试 PASS
- [ ] v2_consumer.py diff ≤ 10 行（只增不减）
- [ ] preflight = 0 issues
- [ ] 现有 v2 consumer P5 V7 PASS 测试仍 PASS（向后兼容）
- [ ] 现有 49 张 Verified 卡未受影响（pytest 全套仍 PASS）

## Exit Criteria

1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex
3. **不要自封 Verified**

## Rollback

1. 恢复 v2_consumer.py 到 HEAD 版本
2. 删除 governance/ 目录
3. 删除 goal_guard_hook.py
4. 删除 test_goal_guard.py / test_goal_guard_hook.py
5. `git reset --hard HEAD~1`（如有 commit）

## Time Budget

45 分钟

## Codex Acceptance Gate

Codex 独立验证：
1. `pytest tests/unit/test_goal_guard.py -v` 15+ case PASS
2. `pytest _agent-hub/v2/tests/test_goal_guard_hook.py -v` 集成测试 PASS
3. `git diff _agent-hub/v2/src/v2_consumer.py` 行数 ≤ 10
4. `pytest _agent-hub/v2/tests/ -v` 既有 v2 测试仍 PASS
5. `pytest tests/unit -v` 全套仍 PASS
6. preflight v4 = 0 issues

全部通过 → status=Verified