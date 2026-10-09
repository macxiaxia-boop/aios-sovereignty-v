---
id: D003
title: Experiment Engine (A/B test)
owner: CC
priority: P0
track: 6 — VNext Phase D (Business)
preconditions: [D002]
estimated_minutes: 120
depends_on: [D002]
blocks: [D007]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `Experiment` (id, name, hypothesis, metric, control_value, treatment_value, winner, p_value, sample_size)
2. `create(name, hypothesis, metric)`: 创建实验
3. `run(exp_id, control_size, treatment_size)`: 跑实验
4. `conclude(exp_id)`: 计算 winner + p_value (用 t-test 或 chi-square)
5. 集成测试 (5 case: create_experiment, run_basic, winner_detection, inconclusive_low_sample, audit)

## Evidence
- [ ] 100 experiments 跑通
- [ ] winner detection ≥ 80% accurate (用 mock data)
- [ ] inconclusive when n < 30
- [ ] pytest 全 PASS
