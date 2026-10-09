---
id: B004
title: Context Compiler（token 高效上下文组装）
owner: CC
priority: P0
track: 4 — VNext Phase B (Context)
preconditions: [B001, B003]
estimated_minutes: 180
depends_on: [B001, B003]
blocks: [B010]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. Pydantic: `CompiledContext` (task_id, compiled: list[ContextChunk], total_tokens<=4096, truncated, elapsed_ms)
2. Pydantic: `ContextChunk` (source ∈ working_memory/long_term_memory/knowledge/skill_registry, content, relevance 0..1, tokens, evidence_id Optional)
3. `ContextCompiler` Protocol 接口
4. 算法:
   - Collect candidates from 4 sources
   - Score relevance (heuristic: keyword overlap + recent access + explicit task.tags)
   - Greedy fill until token_budget=4096
   - Truncate last chunk if > remaining, mark truncated=True
5. Caching: 同一 task_id 第二次调用返回 cache (避免重复 compute)
6. 集成测试 (5 case: token_budget_respect/source_priority/relevance_score/cache_hit/4-source_aggregation)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\context\compiler.py`
- `D:\AIOS\kernel\src\aios_kernel\context\models.py` (ContextChunk, CompiledContext)
- `D:\AIOS\kernel\tests\integration\test_context_compiler.py`

## Out-of-scope
- ❌ RAG / vector store (B005)
- ❌ Knowledge embedding (B005)
- ❌ Skill Registry (B006)
- ❌ 触碰 T0030-T0040 已 Verified 内容
- ❌ 触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Forbidden
- ❌ 不准创建 protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ 不准 compile 结果 > 4096 token

## Evidence Requirements
- [ ] 给定 task + 1000 candidates, compile 后 ≤ 4096 tokens
- [ ] Relevance score ≥ 0.8 在 95% case
- [ ] 4 source priority 正确 (working_memory > long_term > knowledge > skill)
- [ ] Cache hit 第 2 次调用 < 50ms
- [ ] pytest 全 PASS

## Exit Criteria
1. evidence 全勾
2. pytest exit 0
3. status=Submitted

## Time Budget
180 分钟
