# AIOS VNext Phase B — Acceptance Spec v0.1

**Author**: Codex (supervisor)
**Date**: 2026-10-08
**Phase**: Phase B — Context Plane
**Source**: VNext Master Spec V1.0 MASTER §11-§15 (Context Plane) + §29-§97 (sub-rules)
**Schema**: 11 段

---

## §1. Phase B 范围

Phase B 范围限定于 VNext Master Spec §11-§15 五层 Context Plane:

1. **Working Memory** (短时 session state, kernel session-scoped)
2. **Long-term Memory** (持久 knowledge archive, > 30 天保留)
3. **Context Compiler** (token-efficient prompt assembly)
4. **Knowledge** (RAG vector store + chunking + retrieval)
5. **Skill Registry** (consolidate 5 capability registry 版本到 1 canonical)

Plus 3 个 governance gap 修复 (从 T0008 报告继承):
6. **WorkBuddy native AGENTS.md** (delegates to central SSOT)
7. **OpenClaw SSOT link** (CLAUDE.md delegates)
8. **Hermes Agent** (status documented: exists or stub)

Phase C-E 不在本文档。

---

## §2. Phase B 完成判据（10 项硬性指标）

| # | 判据 | 测试方法 | 通过线 |
|---|------|---------|---------|
| **1** | **Working Memory 持久化** | 写 100 KV entry 到 working_memory 表，重启 kernel 进程，从表读出 | 100/100 读出 + entry 全字段一致 |
| **2** | **Long-term Memory 30 天保留** | 写 100 archive entry, 设 created_at = 30 days ago, query | 100/100 仍可检索 + 30-day policy 不删除 |
| **3** | **Context Compiler token 预算** | 给定 task + 1000 context chunks, 编译后 token ≤ 4K | ≥ 95% task 在 4K 内完成 + relevance score ≥ 0.8 |
| **4** | **Knowledge RAG recall** | 100 synthetic query + ground truth doc, retrieval | ≥ 90% recall@5 + chunking 跨 50+ doc 不漏 |
| **5** | **Skill Registry 唯一化** | 检测 5 个旧版本 (v2/v3/v4/v43/v5), 合并到单一 v5 | 5 → 1 registry, 所有 Capability v5 reference 同步 |
| **6** | **Memory + Kernel 集成** | 100-task 闭环 (T0036 复用), 验证 task 间 memory recall | 100/100 + memory recall 工作 |
| **7** | **Skill promotion pipeline** | T0009 5 evolution candidates → 4 register + 1 self-ref archive | 5/5 处置, 注册 4 个 skill |
| **8** | **WorkBuddy native AGENTS.md** | 写入 `C:\Users\xinzh\.workbuddy\AGENTS.md`, 内容 delegate to central SSOT | 文件存在 + 内容含 "delegates to" + hash 对齐 |
| **9** | **OpenClaw SSOT link** | 更新 `C:\Users\xinzh\.openclaw\CLAUDE.md`, 加 delegate header | 文件含 "delegates to" + hash 对齐中央 |
| **10** | **Hermes Agent status** | 文档化 Hermes 状态 (存在/stub/未安装) | 文档路径 + 状态清晰 |

---

## §3. 不可接受（反面清单）

- ❌ Working Memory 写到非 Local 层或重启动丢失
- ❌ Long-term Memory 30 天后被 silent delete
- ❌ Context Compiler 编译结果 > 4K token
- ❌ Knowledge RAG recall < 90%
- ❌ 多版本 Capability registry 并存
- ❌ Skill candidate 只 promote 不测试
- ❌ WorkBuddy/OpenClaw AGENTS 无中央 SSOT 链接
- ❌ Hermes 状态未知

---

## §4. 数据 Schema

```python
# working_memory.py
class WorkingMemoryEntry(BaseModel):
    key: str  # unique within session
    value: JSON
    created_at: datetime
    expires_at: Optional[datetime]
    session_id: UUID4

# long_term_memory.py
class LongTermEntry(BaseModel):
    key: str
    value: JSON
    created_at: datetime
    retention_days: int  # >= 30 default
    tags: List[str]
    source_evidence_id: Optional[UUID4]  # back-link to original

# context_compiler.py
class CompiledContext(BaseModel):
    task_id: UUID4
    compiled: list[ContextChunk]  # ordered by relevance
    total_tokens: int  # <= 4096
    truncated: bool  # if any chunk cut
    elapsed: float

class ContextChunk(BaseModel):
    source: Literal["working_memory", "long_term_memory", "knowledge", "skill_registry"]
    content: str
    relevance: float  # 0..1
    tokens: int
    evidence_id: Optional[UUID4]

# knowledge.py
class Document(BaseModel):
    id: UUID4
    title: str
    content: str
    chunks: List[DocumentChunk]
    embedding: Optional[List[float]]  # pgvector
    source_path: Optional[str]

class DocumentChunk(BaseModel):
    doc_id: UUID4
    content: str
    chunk_index: int
    token_count: int
    embedding: Optional[List[float]]

# skill_registry.py
class Skill(BaseModel):
    id: str  # canonical name, e.g. "ai-router-v5"
    version: str  # semver
    title: str
    description: str
    implementation: str  # code path
    superseded_by: Optional[str]
    promoted_at: Optional[datetime]
```

### 4.1 SQLAlchemy ORM（8 张表）

```sql
working_memory(id PK, session_id, key, value JSON, created_at, expires_at)
long_term_memory(id PK, key, value JSON, created_at, retention_days, tags JSON, source_evidence_id)
documents(id PK, title, content, source_path, created_at)
document_chunks(id PK, doc_id FK, chunk_index, content, token_count)
embeddings(id PK, chunk_id FK, vector VECTOR(1536))  -- pgvector
compiled_contexts(id PK, task_id FK, content JSON, total_tokens, elapsed_ms)
skills(id PK, version, title, description, implementation, superseded_by, promoted_at)
context_chunks(id PK, source, content, relevance, tokens, evidence_id)
```

---

## §5. Context Compiler 协议

```python
class ContextCompiler(Protocol):
    async def compile(
        self,
        task: Task,
        working_memory: WorkingMemory,
        long_term: LongTermMemory,
        knowledge: Knowledge,
        skills: SkillRegistry,
        token_budget: int = 4096,
    ) -> CompiledContext: ...
```

**算法**:
1. **Collect candidates** from 4 sources (working_memory / long_term / knowledge / skill_registry)
2. **Score relevance** (heuristic: keyword overlap + recent access + explicit task.tags)
3. **Greedy fill** until token_budget
4. **Truncate** if last chunk > remaining budget (mark truncated=True)
5. **Return** CompiledContext with provenance

---

## §6. Knowledge RAG 协议

```python
class Knowledge(Protocol):
    async def add_document(self, doc: Document) -> None: ...
    async def chunk(self, doc: Document) -> List[DocumentChunk]: ...  # 500-token chunks
    async def embed(self, chunks: List[DocumentChunk]) -> List[List[float]]: ...
    async def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]: ...
```

**Phase B 实现**：pgvector extension (开发期用 sqlite + 简单 cosine similarity).

---

## §7. Skill Registry Consolidation

**当前 5 版本**: v2/v3/v4/v43/v5 在 `D:\个人文件\AI\Operator\aios_tools\_aios_capability_registry_v*.py`

**Phase B 策略**:
1. 选 v5 作为 canonical (latest, most complete)
2. Migration script: `consolidate_capability_registry.py`
   - Read v2/v3/v4/v43
   - Merge entries into v5 registry
   - Mark v2/v3/v4/v43 as `.deprecated`
   - Write `consolidation_report_<ts>.json`
3. Tests: all entries present in v5 + no duplicates

---

## §8. Skill Promotion Pipeline

**T0009 evolution candidates** (5 个):

| ID | Skill Candidate | Description |
|----|----------------|-------------|
| E001 | `skill/preflight-anti-protocol-explosion` | spawn_agent 时自动跑 preflight, FAIL 立即 rollback |
| E002 | `skill/codex-supervisor-pattern` | Codex spawn_agent 后批量验, 不漏 |
| E003 | `skill/simulation-harness-100task` | 100 mock task + 6 worker + MockClock 压缩 |
| E004 | `skill/5-element-evidence-pattern` | Verified 卡 = 5 要素 (md/preflight/commit/pytest/forbidden) |
| E005 | `skill/aios-evolution-log` | 7 步 growth→reuse 全闭环 |

**Phase B 处置**:
1. **E001-E004** promote → 写入 `D:\AIOS\aios_kernel\skills\` canonical skill registry
2. **E005** self-referential → 写入 `_archived\E005_20261008\` (skill 本身是关于 evolution log 的, 不能 promote 到自身 registry)

---

## §9. Governance Gap Fix

### B007 — WorkBuddy native AGENTS.md
- 路径: `C:\Users\xinzh\.workbuddy\AGENTS.md`
- 内容: 同 `D:\AIOS\_agent-hub\AGENTS.md` 中央 SSOT
- 验证: 文件存在 + 内容含 "delegates to" + hash 对齐

### B008 — OpenClaw SSOT link
- 路径: `C:\Users\xinzh\.openclaw\CLAUDE.md`
- 内容: 加 "delegates to central SSOT" header
- 验证: hash 对齐 + 内容含 delegate 标记

### B009 — Hermes Agent
- 路径: 探测 `D:\AIOS\hermes\` + `C:\Users\xinzh\.hermes\`
- 状态: NOT_FOUND (确认) 或 stub (新建) 或文档化
- 输出: `D:\AIOS\_agent-hub\reports\hermes_status_<ts>.md`

---

## §10. 失败模式

| 失败 | 检测 | 恢复 |
|------|------|------|
| Working Memory 重启丢失 | 重启后 read 测试 fail | 强制 commit 持久化, 加 flush-on-write |
| Long-term Memory 30 天删除 | 30 天后 query fail | retention policy 强制保留, 加 backup |
| Context Compiler > 4K token | compile 测试 fail | 截断最后 chunk, 标记 truncated=True |
| Knowledge RAG recall < 90% | 100 query 测试 fail | 调整 chunk size + embedding model |
| Skill Registry 多版本冲突 | consolidation 测试 fail | 强制 v5 canonical, .deprecated 旧版 |
| Skill promotion 测试失败 | e2e test fail | rollback, archive candidate |

---

## §11. Phase B 通过的签字条件

✅ **全部 10 项判据通过**
✅ **Skill Registry 唯一化**: 5 → 1
✅ **Skill promotion**: 5/5 candidates 处置
✅ **Governance gaps**: 3/3 fix
✅ **Phase B 报告**: `D:\AIOS\_agent-hub\reports\aios_vnext_phase_b_done_<ts>.md`

---

## 附录 A: Phase B 任务卡 ID 体系

- **B001**: Phase B Acceptance Spec (Codex self)
- **B002**: Working Memory
- **B003**: Long-term Memory
- **B004**: Context Compiler
- **B005**: Knowledge RAG
- **B006**: Skill Registry Consolidation
- **B007**: WorkBuddy native AGENTS.md (Codex)
- **B008**: OpenClaw SSOT link (Codex)
- **B009**: Hermes Agent status (Codex)
- **B010**: Memory integration test (dev)
- **B011**: Skill promotion pipeline (Codex + dev)
- **B012**: Phase B comprehensive verification (Codex)
- **B013**: DONE report (Codex self)

---

**Codex Supervisor 签字**:
- Date: 2026-10-08 12:30:00 +08:00
- Authority: AGENTS.md + VNext Spec §11-§15 + §29-§97
- Status: **Verified ✅ (Phase B Acceptance Spec v0.1 定稿)**
- Next: B002-B009 implementation + B010 integration test + B012-B013 verify
