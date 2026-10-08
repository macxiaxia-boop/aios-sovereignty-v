# AIOS VNext Phase C — Acceptance Spec v0.1

**Author**: Codex (supervisor)
**Date**: 2026-10-08
**Phase**: Phase C — Learning Plane
**Source**: VNext Master Spec V1.0 MASTER §16-§27 (Learning + Skill Evolution + Canary + Promotion)
**Schema**: 11 段

---

## §1. Phase C 范围

Phase C = Learning Plane (闭环从 execution → learning → improvement):

1. **Trace Mining** (从 kernel trace 表读 + 提取 patterns)
2. **Failure Pattern Detector** (识别重复失败 + 聚类)
3. **Eval Dataset Builder** (从真实执行 + 合成生成评测集)
4. **Replay Engine** (历史 work flow against new kernel)
5. **Skill Usage Tracker** (track 每 skill 调用次数 + 成功率)
6. **Skill Evolution Pipeline** (deprecate unused + version promotion)
7. **Canary Mechanism** (skill 灰度发布)

Phase D/E 不在本文档。

---

## §2. Phase C 完成判据（10 项硬性指标）

| # | 判据 | 测试方法 | 通过线 |
|---|------|---------|---------|
| **1** | **Trace Mining 提取 patterns** | 100 真实 trace → extract success/failure patterns | ≥ 80% patterns 准确 |
| **3** | **Failure Pattern Detector 聚类** | 50 个 failure → cluster → 5 个 root cause | 5 cluster, 0 misclassification |
| **4** | **Eval Dataset Builder 自动生成** | 100 synthetic + 100 from real = 200 case dataset | 200/200 generated |
| **5** | **Replay Engine 跑历史** | replay 100 historical run against new kernel | 100/100 跑通 + diff detection |
| **6** | **Skill Usage Tracker** | 5 skills × 100 task = 500 calls → tracker 记录 | 500/500 captured |
| **7** | **Skill Deprecation 自动** | unused 30 days → mark deprecated | 100% 自动检测 |
| **8** | **Skill Canary** | new skill 灰度 5% → monitor → promote 100% | 100% canary flow |
| **9** | **Learning Loop 闭环** | trace → failure → eval → replay → skill promotion 全链 | 1 完整周期 |
| **10** | **Phase C Done report** | D:\AIOS\_agent-hub\reports\aios_vnext_phase_c_done_<ts>.md | 11 段 |

---

## §3. 不可接受（反面清单）

- ❌ Trace Mining 提取假 pattern (over-extraction)
- ❌ Failure detector 漏掉 critical failure (silent skip)
- ❌ Eval dataset 全是 synthetic 无 real evidence
- ❌ Replay 跟 prod 不一致
- ❌ Skill 静默 deprecate (无 audit)
- ❌ Canary 跳步 (full deploy 没用 canary)
- ❌ Learning Loop 不闭环

---

## §4. 数据 Schema

```python
# trace_mining.py
class TracePattern(BaseModel):
    id: str
    pattern_type: Literal["success", "failure", "anomaly"]
    description: str
    frequency: int  # occurrences in traces
    first_seen: datetime
    last_seen: datetime
    example_trace_ids: list[str]
    evidence_source: Optional[str]

class FailureCluster(BaseModel):
    id: str
    root_cause: str
    affected_traces: list[str]
    occurrence_count: int
    severity: Literal["low", "medium", "high", "critical"]
    recommended_fix: Optional[str]

# eval_dataset.py
class EvalCase(BaseModel):
    id: str
    query: str
    expected_output: Any
    source: Literal["synthetic", "real"]
    difficulty: Literal["easy", "medium", "hard"]
    evidence_id: Optional[str]  # back-link to real

# skill_evolution.py
class SkillVersion(BaseModel):
    skill_id: str
    version: str
    promoted_at: Optional[datetime]
    deprecated_at: Optional[datetime]
    canary_pct: int  # 0-100
    usage_count: int
    success_count: int
    failure_count: int

# canary.py
class CanaryDeployment(BaseModel):
    id: str
    skill_id: str
    skill_version: str
    started_at: datetime
    canary_pct: int  # 0-100
    current_step: Literal["shadow", "5pct", "25pct", "50pct", "100pct", "rolled_back"]
    metric_promotion: dict  # error_rate / latency / throughput
```

---

## §5. Trace Mining Protocol

```python
class TraceMiner(Protocol):
    async def mine(self, traces: list[TraceSpan], time_range: tuple) -> list[TracePattern]: ...
    async def extract_failure_clusters(self, patterns: list[TracePattern]) -> list[FailureCluster]: ...
```

**算法**:
1. 收集 time_range 内的 traces
2. 按 event_type 分类 (success/failure)
3. 失败 trace 聚类 (相似失败模式)
4. 提取 pattern description (top 关键词 + 共同 step)
5. 关联 example trace IDs

---

## §6. Failure Pattern Detector Protocol

```python
class FailureDetector(Protocol):
    async def detect(self, traces: list[TraceSpan]) -> list[FailureCluster]: ...
    async def prioritize(self, clusters: list[FailureCluster]) -> list[FailureCluster]: ...  # by severity
```

**算法**:
1. 失败 trace 分组 (按 error message hash)
2. 同 group 聚类 → cluster
3. cluster root_cause 提取 (LLM or heuristic)
4. severity 评分 (occurrence × impact)

---

## §7. Eval Dataset Builder

```python
class EvalDatasetBuilder(Protocol):
    async def from_real(self, traces: list[TraceSpan], n: int = 100) -> list[EvalCase]: ...
    async def synthetic(self, n: int = 100) -> list[EvalCase]: ...
    async def merge(self, real: list[EvalCase], synth: list[EvalCase]) -> list[EvalCase]: ...
```

---

## §8. Replay Engine

```python
class ReplayEngine(Protocol):
    async def replay(self, historical_run: dict, new_kernel: 'Kernel') -> ReplayResult: ...
    async def diff_detect(self, expected: dict, actual: dict) -> list[str]: ...
```

---

## §9. Skill Evolution Pipeline

```python
class SkillEvolutionPipeline(Protocol):
    async def track_usage(self, skill_id: str) -> None: ...
    async def detect_deprecated(self, unused_days: int = 30) -> list[SkillVersion]: ...
    async def propose_new_version(self, skill_id: str, improvements: list[str]) -> SkillVersion: ...
```

---

## §10. Canary Mechanism

5-step canary flow:
1. **Shadow** (0%): log only, no actual deploy
2. **5%** (early signal)
3. **25%** (broader validation)
4. **50%** (majority confidence)
6. **100%** (promoted to prod)

Auto-rollback on error_rate > 1% or latency > 2x baseline.

---

## §11. Phase C 通过的签字条件

✅ **全部 10 项判据通过** (with caveat docs)
✅ **Learning Loop 闭环**: trace → failure → eval → replay → skill promotion
✅ **Phase C 报告**: `D:\AIOS\_agent-hub\reports\aios_vnext_phase_c_done_<ts>.md`

---

**Codex Supervisor 签字**:
- Date: 2026-10-08 13:00:00 +08:00
- Authority: AGENTS.md + VNext Spec §16-§27
- Status: **Verified ✅ (Phase C Acceptance Spec v0.1 定稿)**
- Next: C002-C008 implementation + C009 verification + C010 done
