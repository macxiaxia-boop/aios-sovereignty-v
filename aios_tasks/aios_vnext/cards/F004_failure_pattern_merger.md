---
id: F004
title: Failure Pattern Merger — 失败模式归并器
owner: CC
priority: P0
track: 6 — VNext Phase F (Cognitive Governance)
preconditions: [F003, C003]
estimated_minutes: 45
depends_on: [F003, C003]
blocks: [F005]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

把 `learning/failure_detector.py` 升级为归并器（不只是检测），把 50 个相似失败归并到 ≤10 个 cluster，归并率 ≥70%。

### 1. 必建/改文件（白名单内）

**`D:\AIOS\kernel\src\aios_kernel\learning\clustering.py`** — 新建聚类算法：

```python
"""clustering.py — Failure pattern clustering (F004)."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class FailureTrace:
    """输入：单条失败 trace"""
    id: str
    error_message: str
    error_type: str
    context: dict
    timestamp: str  # ISO 8601


@dataclass
class FailureCluster:
    """输出：归并后的 cluster"""
    cluster_id: str
    root_cause: str
    error_type: str
    affected_trace_ids: list[str]
    occurrence_count: int
    severity_score: float
    first_seen: str
    last_seen: str
    recommended_fix: str
    sample_error_messages: list[str]  # 最多 5 个


class FailurePatternMerger:
    """失败模式归并器"""
    
    def __init__(self, eps: float = 0.15, min_samples: int = 2):
        self.eps = eps
        self.min_samples = min_samples
    
    def _normalize(self, error_message: str) -> str:
        """normalize error message (strip paths/numbers/timestamps)"""
        import re
        s = error_message
        s = re.sub(r"[A-Z]:\\[\w\\\.\-]+", "<PATH>", s)  # Windows paths
        s = re.sub(r"\d+\.\d+\.\d+\.\d+", "<IP>", s)  # IPs
        s = re.sub(r"\b\d+\b", "<NUM>", s)  # numbers
        s = re.sub(r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b", "<UUID>", s)
        s = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", "<TS>", s)
        return s.strip()
    
    def _hash(self, normalized: str) -> str:
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _severity(self, occurrence: int, impact: float = 1.0) -> float:
        return min(10.0, occurrence * impact)
    
    def _root_cause(self, error_type: str, normalized_msg: str) -> str:
        # 启发式根因提取（不调 LLM）
        if "PermissionError" in error_type or "permission" in normalized_msg:
            return "permission_denied"
        if "FileNotFound" in error_type or "no such file" in normalized_msg:
            return "file_missing"
        if "TimeoutError" in error_type or "timeout" in normalized_msg:
            return "timeout"
        if "ConnectionError" in error_type or "connection" in normalized_msg:
            return "network_unavailable"
        if "ValidationError" in error_type or "validation" in normalized_msg:
            return "input_invalid"
        return f"unknown:{error_type}"
    
    def _recommend_fix(self, root_cause: str) -> str:
        fixes = {
            "permission_denied": "Check file/dir permissions; ensure process runs as required user",
            "file_missing": "Verify file exists at expected path; create if needed",
            "timeout": "Increase timeout; check if service is overloaded",
            "network_unavailable": "Check connectivity; verify service is reachable",
            "input_invalid": "Validate input schema; add pre-check",
        }
        return fixes.get(root_cause, "Investigate manually; add specific check")
    
    def merge(self, failures: list[FailureTrace]) -> list[FailureCluster]:
        """主入口：失败 trace 列表 → 归并 cluster 列表"""
        if not failures:
            return []
        
        # Step 1: normalize + hash
        groups = defaultdict(list)
        for f in failures:
            norm = self._normalize(f.error_message)
            h = self._hash(norm)
            groups[h].append((f, norm))
        
        # Step 2: cluster by hash (同一归一化 = 同 cluster)
        clusters = []
        for h, items in groups.items():
            if len(items) < self.min_samples:
                # 单次失败仍记录为 cluster，但 severity 低
                pass
            
            trace_ids = [it[0].id for it in items]
            first_sample = items[0][0]
            timestamps = sorted([it[0].timestamp for it in items])
            
            cluster = FailureCluster(
                cluster_id=h,
                root_cause=self._root_cause(first_sample.error_type, items[0][1]),
                error_type=first_sample.error_type,
                affected_trace_ids=trace_ids,
                occurrence_count=len(items),
                severity_score=self._severity(len(items)),
                first_seen=timestamps[0],
                last_seen=timestamps[-1],
                recommended_fix=self._recommend_fix(self._root_cause(first_sample.error_type, items[0][1])),
                sample_error_messages=[it[0].error_message for it in items[:5]],
            )
            clusters.append(cluster)
        
        # Step 3: sort by severity desc
        clusters.sort(key=lambda c: c.severity_score, reverse=True)
        return clusters


def merge_rate(original_count: int, clusters: list[FailureCluster]) -> float:
    """归并率 = 1 - cluster_count / original_count"""
    if original_count == 0:
        return 0.0
    return 1.0 - (len(clusters) / original_count)
```

**`D:\AIOS\kernel\src\aios_kernel\learning\merger.py`** — 与 GoalContract 集成：

```python
"""merger.py — Failure clusters → GoalContract 反哺 (F004 + F001 集成)."""
from __future__ import annotations

from aios_kernel.learning.clustering import FailurePatternMerger, FailureTrace, FailureCluster, merge_rate
from aios_kernel.domain.goal import Goal, FailureMode


def clusters_to_failure_modes(clusters: list[FailureCluster], min_occurrence: int = 3) -> list[FailureMode]:
    """把 cluster 转成 GoalContract.failure_modes"""
    modes = []
    for c in clusters:
        if c.occurrence_count < min_occurrence:
            continue
        modes.append(FailureMode(
            description=f"[{c.root_cause}] {c.error_type} (occurs {c.occurrence_count}x)",
            detection=f"error_type={c.error_type}; normalized_hash={c.cluster_id[:8]}",
            indicator=c.sample_error_messages[0] if c.sample_error_messages else None,
        ))
    return modes


def suggest_preserve_capabilities(clusters: list[FailureCluster]) -> list[str]:
    """从 cluster 提取应保留的能力"""
    # 简化：建议保留的能力 = 反向：哪些不能破坏
    return [
        "verifier/deterministic.py (don't touch)",
        "v2 consumer main loop (don't refactor)",
        "AGENTS.md SSOT",
    ]
```

### 2. 单元测试（15+ case）

**`D:\AIOS\kernel\tests\unit\test_failure_pattern_merger.py`**：

```python
# Normalize
def test_normalize_strips_windows_paths()
def test_normalize_strips_ips()
def test_normalize_strips_numbers()
def test_normalize_strips_uuids()
def test_normalize_strips_timestamps()
# Hash consistency
def test_same_message_same_hash()
def test_different_message_different_hash()
# Cluster
def test_empty_input_returns_empty()
def test_single_failure_returns_one_cluster()
def test_50_similar_failures_cluster_to_leq_10()
def test_50_dissimilar_failures_no_merge()
def test_min_samples_filters_singletons()
# Severity
def test_severity_increases_with_occurrence()
def test_severity_capped_at_10()
# Root cause
def test_root_cause_permission_error()
def test_root_cause_file_not_found()
def test_root_cause_timeout()
def test_root_cause_unknown_fallback()
# Integration with GoalContract
def test_clusters_to_failure_modes_min_occurrence()
def test_suggest_preserve_capabilities_returns_list()
# Merge rate
def test_merge_rate_50_to_5_is_90pct()
def test_merge_rate_50_to_50_is_0pct()
def test_merge_rate_empty_is_0()
# Performance
def test_1000_failures_processed_under_1_second()
```

### 3. Integration 测试（关键）

**`D:\AIOS\kernel\tests\integration\test_failure_merger_integration.py`**：

```python
def test_50_real_failures_merged_to_clusters():
    """模拟 50 个真实失败 trace（mix 相似+相异），验证归并率 ≥70%"""
    failures = generate_realistic_failures(50)  # helper
    merger = FailurePatternMerger()
    clusters = merger.merge(failures)
    rate = merge_rate(50, clusters)
    assert rate >= 0.70, f"merge rate {rate:.2%} < 70%"
    assert len(clusters) <= 10

def test_clusters_can_be_loaded_into_goal_contract():
    failures = generate_realistic_failures(20)
    clusters = FailurePatternMerger().merge(failures)
    modes = clusters_to_failure_modes(clusters)
    goal = Goal(title="test", success_criteria="x", budget=0, owner="codex",
                failure_modes=modes)
    assert len(goal.failure_modes) > 0
```

## Out-of-scope (不要做)

- ❌ 不重写 failure_detector.py（F004 在它之上加 cluster，不替换）
- ❌ 不调 LLM（只用启发式 + hash）
- ❌ 不实现 GoalGuard Hook（F005 才做）
- ❌ 不改 Goal 模型（F001 已扩）
- ❌ 不动 DecisionAuditORM（F003 已建）
- ❌ 不创建 `_v6_*.py` / `_r*.py` / `protocol_*.md` 等 forbidden

## Inputs (必须先读)

1. `D:\AIOS\kernel\src\aios_kernel\learning\failure_detector.py` — 现有 detector（2544B）
2. `D:\AIOS\kernel\src\aios_kernel\learning\trace_miner.py` — FailureTrace 来源（2109B）
3. `D:\AIOS\kernel\src\aios_kernel\domain\goal.py` — FailureMode schema（F001 已加）
4. `D:\AIOS\aios_tasks\aios_vnext\cards\F001_goal_contract_12_fields.md`
5. `D:\AIOS\aios_tasks\aios_vnext\cards\C003_failure_detector.md`

## Outputs (必须产出)

1. `D:\AIOS\aios_tasks\aios_vnext\evidence\F004__<ts>.md` — 必含 preflight 附件
2. `D:\AIOS\kernel\src\aios_kernel\learning\clustering.py`
3. `D:\AIOS\kernel\src\aios_kernel\learning\merger.py`
4. `D:\AIOS\kernel\tests\unit\test_failure_pattern_merger.py` — 15+ case
5. `D:\AIOS\kernel\tests\integration\test_failure_merger_integration.py` — 关键集成测试

## Evidence Requirements

- [ ] FailurePatternMerger.merge() 可 import + 调用
- [ ] 50 similar failures → ≤10 clusters
- [ ] merge_rate ≥ 70%
- [ ] clusters_to_failure_modes() 返回非空 list（occurrence ≥ 3）
- [ ] clusters → GoalContract.failure_modes 加载成功
- [ ] `pytest tests/unit/test_failure_pattern_merger.py -v` 15+ case PASS
- [ ] `pytest tests/integration/test_failure_merger_integration.py -v` 集成测试 PASS
- [ ] 1000 failures < 1s 处理（性能）
- [ ] preflight = 0 issues
- [ ] 现有 49 张 Verified 卡未受影响（pytest 全套仍 PASS）

## Exit Criteria

1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex
3. **不要自封 Verified**

## Rollback

1. 删除 clustering.py / merger.py
2. 删除 test_failure_pattern_merger.py / test_failure_merger_integration.py
3. `git reset --hard HEAD~1`（如有 commit）

## Time Budget

45 分钟

## Codex Acceptance Gate

Codex 独立验证：
1. `pytest tests/unit/test_failure_pattern_merger.py tests/integration/test_failure_merger_integration.py -v` 全 PASS
2. `pytest tests/unit -v` 全套仍 PASS
3. 手动跑 `merge_rate(50, clusters)` ≥ 0.70 验证
4. preflight v4 = 0 issues

全部通过 → status=Verified