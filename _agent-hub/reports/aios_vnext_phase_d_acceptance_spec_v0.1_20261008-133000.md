# AIOS VNext Phase D — Acceptance Spec v0.1

**Author**: Codex (supervisor)
**Date**: 2026-10-08
**Phase**: Phase D — Business Intelligence
**Source**: VNext Master Spec V1.0 MASTER §17-§22 (Industry Scout + Experiment + CRM + Marketing + Business Outcome)
**Schema**: 11 段

---

## §1. Phase D 范围

Phase D = Business Intelligence Plane:

1. **Industry Scout** (外部信号监控: market signals, competitor moves, regulatory)
3. **Experiment Engine** (A/B test framework for business strategies)
4. **CRM Feedback** (客户反馈 → 决策 learning loop)
5. **Marketing Feedback** (营销反馈 → skill promotion)
6. **Business Outcome** (KPI 跟踪 + outcome validation)

Phase E 不在本文档。

---

## §2. Phase D 完成判据（8 项硬性指标）

| # | 判据 | 测试方法 | 通过线 |
|---|------|---------|---------|
| **1** | **Industry Scout 信号收集** | 100 signals → classify 5 categories | 100/100 classified |
| **3** | **Experiment Engine A/B test** | 100 experiments 跑通, 显著 winner detection | ≥ 80% accurate winner |
| **4** | **CRM Feedback ingestion** | 1000 customer events → 5 categories | 1000/1000 ingested |
| **5** | **Marketing Feedback loop** | 100 campaigns → 5 metric categories | 100/100 measured |
| **6** | **Business Outcome KPI** | 20 KPI dashboard 实时 | ≥ 95% data fresh |
| **7** | **D→C feedback loop** | outcome → skill promotion | 1 闭环 |
| **8** | **Phase D Done report** | D:\AIOS\_agent-hub\reports\aios_vnext_phase_d_done_<ts>.md | 11 段 |

---

## §3. 不可接受

- ❌ Industry Scout 全 spam (不处理)
- ❌ Experiment Engine 假 winner (false positive)
- ❌ CRM data 未脱敏 (privacy violation)
- ❌ Marketing 假 metrics
- ❌ Business Outcome 全靠 mock (假 OK)

---

## §4. 数据 Schema

```python
class IndustrySignal(Envelope):
    source: str  # "rss" | "api" | "manual"
    category: Literal["product", "competitor", "regulatory", "market", "tech"]
    title: str
    content: str
    url: Optional[str]
    confidence: float  # 0-1
    action_required: bool

class Experiment(Envelope):
    name: str
    hypothesis: str
    metric: str
    control_value: float
    treatment_value: float
    winner: Literal["control", "treatment", "inconclusive"]
    p_value: float
    sample_size: int

class CRMEvent(Envelope):
    customer_id_hash: str  # hashed for privacy
    event_type: Literal["churn", "upsell", "support", "feedback", "purchase"]
    severity: str  # "low" | "medium" | "high"
    product: str
    action_recommended: Optional[str]

class MarketingCampaign(Envelope):
    name: str
    channel: str  # "email" | "social" | "ads" | "organic"
    impressions: int
    conversions: int
    cost: float
    roi: float
    skill_id: Optional[str]  # promote skill from this

class BusinessKPI(Envelope):
    name: str
    value: float
    target: float
    trend: Literal["up", "down", "stable"]
    freshness: float  # 0-1 (1 = fresh, 0 = stale)
```

---

## §5. Industry Scout Protocol

```python
class IndustryScout(Protocol):
    async def collect(self, sources: list[str]) -> list[IndustrySignal]: ...
    async def classify(self, signal: IndustrySignal) -> IndustrySignal: ...  # 5 categories
    async def alert(self, signal: IndustrySignal, threshold: float) -> bool: ...
```

---

## §6. Experiment Engine Protocol

```python
class ExperimentEngine(Protocol):
    async def create(self, name, hypothesis, metric) -> Experiment: ...
    async def run(self, exp_id: str, control_size: int, treatment_size: int) -> Experiment: ...
    async def conclude(self, exp_id: str) -> Experiment: ...  # winner + p_value
```

---

## §7. CRM Feedback Ingestion

```python
class CRMIngestion(Protocol):
    async def ingest_event(self, event: dict) -> CRMEvent: ...
    async def categorize(self, events: dict) -> dict: ...  # 5 categories
```

---

## §8. Marketing Feedback Loop

```python
class MarketingFeedback(Protocol):
    async def track_campaign(self, campaign: MarketingCampaign) -> dict: ...
    async def recommend_skill_promotion(self, campaign: MarketingCampaign) -> Optional[str]: ...
```

---

## §9. Business Outcome KPI

```python
class BusinessKPI(Protocol):
    async def track_kpi(self, name: str, value: float) -> BusinessKPI: ...
    async def dashboard(self) -> dict: ...  # 20 KPIs
```

---

## §10. 失败模式

| 失败 | 检测 | 恢复 |
|------|------|------|
| Industry Scout 全 spam | filter confidence < 0.3 | drop |
| Experiment low sample | n < 100 | inconclusive |
| CRM 数据未脱敏 | check hash | reject |
| Marketing 假 metrics | cross-validate | reset |

---

## §11. Phase D 通过签字

✅ 8/8 满足
✅ D→C 闭环 (outcome → skill promotion)
✅ Phase D 报告

---

**Codex Supervisor 签字**:
- Date: 2026-10-08 13:30:00 +08:00
- Status: Verified (Phase D Acceptance Spec v0.1)
