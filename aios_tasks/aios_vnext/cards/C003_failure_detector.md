---
id: C003
title: Failure Pattern Detector
owner: CC
priority: P0
track: 5 — VNext Phase C (Learning)
preconditions: [C002]
estimated_minutes: 90
depends_on: [C002]
blocks: [C004, C009]
status: Pending
created: 2026-10-08
---

## Scope
1. Pydantic: `FailureCluster` (id, root_cause, affected_traces, occurrence_count, severity, recommended_fix)
2. 算法: 失败 trace 按 error message hash 分组 → 聚类
3. root_cause 提取 (heuristic, 不调 LLM)
4. severity 评分 (occurrence × impact)
5. 集成测试 (5 case: detect_single_failure, cluster_similar_failures, prioritize, severity_sort, output_format)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\learning\failure_detector.py`
- `D:\AIOS\kernel\tests\integration\test_failure_detector.py`

## Out-of-scope
- ❌ Trace Mining (C002)
- ❌ Eval/Replay/Skill

## Forbidden
- ❌ protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ 调 LLM (只用 deterministic)

## Evidence
- [ ] 50 failure → 5 cluster, 0 misclassification
- [ ] priority by severity
- [ ] pytest 全 PASS

## Time Budget
90 分钟
