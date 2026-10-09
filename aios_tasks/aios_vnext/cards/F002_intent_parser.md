---
id: F002
title: Intent Parser — 用户文本 → GoalContract 解析器
owner: CC
priority: P0
track: 6 — VNext Phase F (Cognitive Governance)
preconditions: [F001]
estimated_minutes: 90
depends_on: [F001]
blocks: [F005]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

把用户的自然语言输入（命令/陈述/问题/带约束/带取舍 5 类）解析成 GoalContract。

### 1. 必建文件（白名单内）

**`D:\AIOS\kernel\src\aios_kernel\intent\__init__.py`** — 空

**`D:\AIOS\kernel\src\aios_kernel\intent\parser.py`** — 主解析器：

```python
class IntentParser:
    """用户文本 → GoalContract 解析器（rule + LLM hybrid）"""
    
    def __init__(self, llm_adapter=None, rule_db=None):
        self.llm = llm_adapter  # 可选；None 时纯 rule
        self.rule_db = rule_db or default_rules()
    
    def parse(self, user_text: str, context: EnvSnapshot | None = None) -> GoalContract:
        """
        流程：
          1. rule-based 预处理（识别命令动词/约束关键词/取舍关键词）
          2. 提取 stated_goal（必填）
          3. 提取 known_constraints（regex 模式）
          4. 提取 approved_tradeoffs（"宁可 X 不要 Y" 模式）
          5. 提取 inferred_intent（LLM 补全，rule 给候选）
          6. 标 missing_evidence（rule 失败项）
          7. 标 permission_scope（默认保守）
          8. 标 autonomous_scope / requires_authorization（基于 stated_goal 类型）
        """
```

**`D:\AIOS\kernel\src\aios_kernel\intent\rules.py`** — Rule patterns：

```python
CONSTRAINT_PATTERNS = [
    (r"(?:不要|禁止|避免)[\s]*(.{2,20})", "scope"),  # 禁止路径/动作
    (r"预算[≤不超]?\s*(\d+)", "budget"),
    (r"(\d+)\s*(?:分钟|min|小时|h|天|d|秒|s)", "timeout"),
    (r"(?:尽快|紧急|马上)", "priority_high"),
]

TRADEOFF_PATTERNS = [
    (r"(?:宁可|宁愿|可以).{0,20}(?:不|不要).{0,20}", "approved_tradeoff"),
    (r"(?:代价|成本).{0,20}(?:是|为).{0,20}", "cost_explicit"),
]

INTENT_CLASSIFIER = {
    "命令类": [r"^(?:做|写|建|修|删|改|跑|查|看|打开|关闭|启动|停止)"],
    "陈述类": [r"^(?:当前|现在|我|我们).{0,10}(?:需要|想|打算|正在)"],
    "问题类": [r"(?:怎么|为什么|什么|哪个|哪里).{0,5}(?:做|办|解决)"],
    "带约束类": [r"在.{2,20}(?:下|里|上|中).{0,10}(?:做|写|跑|查)"],
    "带取舍类": [r"(?:宁可|宁愿).{0,20}(?:不|不要).{0,20}"],
}
```

**`D:\AIOS\kernel\src\aios_kernel\intent\classifier.py`** — IntentType 分类：

```python
class IntentType(str, Enum):
    COMMAND = "command"        # "做X"
    STATEMENT = "statement"    # "我们正在Y"
    QUESTION = "question"      # "怎么Z"
    CONSTRAINED = "constrained" # "在A条件下做B"
    TRADEOFF = "tradeoff"      # "宁可C不要D"
    UNKNOWN = "unknown"
```

### 2. 集成测试（5 类输入各 ≥3 case = 15+ case）

**`D:\AIOS\kernel\tests\unit\test_intent_parser.py`**：

```python
# 命令类
def test_parse_command_simple()  # "建一个营销活动"
def test_parse_command_with_target()  # "在 D:/AIOS/kernel 建一个新文件"
def test_parse_command_imperative()  # "立即停止 v2 consumer"
# 陈述类
def test_parse_statement_need()  # "我需要把今天的工作收尾"
def test_parse_statement_progress()  # "我们正在做 Phase F"
def test_parse_statement_intent()  # "我想了解你的决策过程"
# 问题类
def test_parse_question_how()  # "怎么让 AIOS 知道用户的目标"
def test_parse_question_why()  # "为什么 GoalContract 需要 12 字段"
def test_parse_question_what()  # "什么是 failure_modes"
# 带约束类
def test_parse_constrained_path()  # "在 D:/AIOS 内 不要改 verifier"
def test_parse_constrained_budget()  # "预算 ≤500 元 做一个营销工具"
def test_parse_constrained_timeout()  # "30 分钟内 完成 P5 V8"
# 带取舍类
def test_parse_tradeoff_ke_neng()  # "宁可慢 不要出错"
def test_parse_tradeoff_accept()  # "可以牺牲可读性换性能"
def test_parse_tradeoff_reject()  # "不要为了快 牺牲正确性"
# 混合类
def test_parse_mixed_command_constraint_tradeoff()  # "30 分钟内完成 GoalContract，宁可慢不要出错"
def test_parse_missing_evidence_detected()  # 输入缺关键信息时返回 missing_evidence 非空
def test_parse_unknown_intent_fallback()  # 完全无法分类时返回 IntentType.UNKNOWN + missing_evidence
```

### 3. LLM 适配器接口（可选注入）

**`D:\AIOS\kernel\src\aios_kernel\intent\llm_adapter.py`**：

```python
class LLMAdapter(Protocol):
    """LLM 适配器接口（rule 失败时 fallback）"""
    def infer_intent(self, user_text: str, candidates: list[str]) -> str | None: ...
    def classify_intent(self, user_text: str) -> IntentType | None: ...

class NullLLMAdapter:
    """默认空实现（rule-only 模式）"""
    def infer_intent(self, user_text, candidates): return None
    def classify_intent(self, user_text): return None
```

## Out-of-scope (不要做)

- ❌ 不调用真实 LLM（只定义接口，不接 OpenAI/Anthropic）
- ❌ 不实现 Decision Audit Log（F003 才做）
- ❌ 不实现 Failure Pattern Merger（F004 才做）
- ❌ 不实现 GoalGuard Hook（F005 才做）
- ❌ 不改现有 Goal 模型（F001 才改）
- ❌ 不动 context/compiler.py（只读复用）
- ❌ 不动 v2 consumer / v2_consumer.py
- ❌ 不创建 `_v6_*.py` / `_r*.py` / `protocol_*.md` / `intent_v1.md` 等 forbidden

## Inputs (必须先读)

1. `D:\AIOS\kernel\src\aios_kernel\domain\goal.py` — GoalContract schema（F001 输出）
2. `D:\AIOS\aios_tasks\aios_vnext\cards\F001_goal_contract_12_fields.md` — 12 字段定义
3. `D:\AIOS\aios_tasks\aios_vnext\cards\F000_phase_f_acceptance_spec.md` — Phase F spec

## Outputs (必须产出)

1. `D:\AIOS\aios_tasks\aios_vnext\evidence\F002__<ts>.md` — 必含 preflight 附件
2. `D:\AIOS\kernel\src\aios_kernel\intent\__init__.py`
3. `D:\AIOS\kernel\src\aios_kernel\intent\parser.py`
4. `D:\AIOS\kernel\src\aios_kernel\intent\rules.py`
5. `D:\AIOS\kernel\src\aios_kernel\intent\classifier.py`
6. `D:\AIOS\kernel\src\aios_kernel\intent\llm_adapter.py`
7. `D:\AIOS\kernel\tests\unit\test_intent_parser.py` — 15+ case

## Evidence Requirements

- [ ] IntentParser 可 `from aios_kernel.intent.parser import IntentParser`
- [ ] 5 类输入（命令/陈述/问题/带约束/带取舍）各 ≥3 case PASS
- [ ] 混合输入能同时提取 stated_goal + known_constraints + approved_tradeoffs
- [ ] 无法分类时返回 IntentType.UNKNOWN + missing_evidence 非空
- [ ] NullLLMAdapter 是默认实现，不依赖外部 LLM
- [ ] `pytest tests/unit/test_intent_parser.py -v` 全 PASS
- [ ] 现有 49 张 Verified 卡未受影响（pytest 全套仍 PASS）
- [ ] preflight = 0 issues

## Exit Criteria

1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex
3. **不要自封 Verified**

## Rollback

1. `rm -rf D:\AIOS\kernel\src\aios_kernel\intent\` （如未提交）
2. `git reset --hard HEAD~1`（如有 commit）
3. 删除 `tests/unit/test_intent_parser.py`

## Time Budget

90 分钟

## Codex Acceptance Gate

Codex 独立验证：
1. `pytest tests/unit/test_intent_parser.py -v` 至少 15 case PASS
2. `pytest tests/unit -v` 全套仍 PASS
3. 手动测试 5 类输入各 1 例，确认返回结构正确
4. 抽样 5 个规则模式（CONSTRAINT_PATTERNS / TRADEOFF_PATTERNS / INTENT_CLASSIFIER）命中真实输入
5. preflight v4 = 0 issues

全部通过 → status=Verified