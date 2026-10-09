---
id: C004
title: Eval Dataset Builder
owner: CC
priority: P0
track: 5 — VNext Phase C (Learning)
preconditions: [C003]
estimated_minutes: 90
depends_on: [C003]
blocks: [C005, C009]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `EvalCase` (id, query, expected_output, source, difficulty, evidence_id)
2. `from_real(traces, n=100)`: 从 traces 抽取 case
3. `synthetic(n=100)`: 程序生成 case (覆盖边界 + 常见模式)
4. `merge(real, synth)`: 合并去重
5. 集成测试 (5 case: from_real, synthetic, merge, dedup, format)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\learning\eval_builder.py`
- `D:\AIOS\kernel\tests\integration\test_eval_builder.py`

## Out-of-scope
- ❌ Trace/Failure/Replay/Skill

## Forbidden
- ❌ protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ eval dataset 全 synthetic (必须 mix)

## Evidence
- [ ] 100 synthetic + 100 real = 200 case 全数 generated
- [ ] mix source 平衡 (50% real, 50% synth)
- [ ] pytest 全 PASS

## Time Budget
90 分钟
