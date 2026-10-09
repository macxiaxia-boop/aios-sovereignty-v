---
id: B005
title: Knowledge RAG (vector store + chunking + retrieval)
owner: CC
priority: P0
track: 4 — VNext Phase B (Context)
preconditions: [B001]
estimated_minutes: 240
depends_on: [B001]
blocks: [B004, B010]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. Pydantic: `Document` (id, title, content, chunks[], source_path) + `DocumentChunk` (doc_id, content, chunk_index, token_count, embedding Optional[List[float]])
2. SQLAlchemy ORM: `documents` + `document_chunks` + `embeddings` (用 pgvector 在生产; 开发期用 sqlite + numpy cosine)
3. Chunking: split content by 500-token chunks (with overlap 50)
4. Embedding: dev 期用简单 hash-based 1536-dim vector (或 random placeholder, TBD by CC); prod 期接 OpenAI/Cohere
5. Knowledge Protocol 接口: `add_document / chunk / embed / retrieve(query, top_k=5)`
6. **100 synthetic query test**: recall@5 ≥ 90%

## 路径
- `D:\AIOS\kernel\src\aios_kernel\context\knowledge.py`
- `D:\AIOS\kernel\src\aios_kernel\context\embedding.py`
- `D:\AIOS\kernel\src\aios_kernel\persistence\` (新增 3 models)
- `D:\AIOS\kernel\tests\integration\test_knowledge_rag.py`

## 100 Synthetic Query Test
- 创建 100 ground-truth (query, relevant_doc_id) pairs
- 跑 retrieve(query, top_k=5)
- 计算 recall@5: 100 pair 中 ≥ 90 pair 包含 relevant_doc_id

## Out-of-scope
- ❌ Working/Long-term Memory (B002/B003)
- ❌ Context Compiler (B004)
- ❌ Skill Registry (B006)
- ❌ 真实 OpenAI API 调用 (dev 期用 hash placeholder)
- ❌ 触碰 T0030-T0040 已 Verified 内容
- ❌ 触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Forbidden
- ❌ 不准创建 protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ 不准真实 API 调用 (env 必须没有 OPENAI_API_KEY)

## Evidence Requirements
- [ ] 100 synthetic query recall@5 ≥ 90%
- [ ] chunking 跨 50+ doc 不漏
- [ ] embedding dimension = 1536
- [ ] pytest 全 PASS
- [ ] preflight CLEAN

## Exit Criteria
1. evidence 全勾
2. pytest exit 0
3. status=Submitted

## Time Budget
240 分钟
