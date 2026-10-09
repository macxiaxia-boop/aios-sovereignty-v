"""__init__.py - aios_kernel.context (Phase B B002-B005)."""
from aios_kernel.context.working_memory import (
    DEFAULT_TTL,
    WorkingMemoryEntry,
    WorkingMemoryService,
)
from aios_kernel.context.long_term_memory import (
    MIN_RETENTION_DAYS,
    LongTermEntry,
    LongTermMemoryService,
    RetentionPolicyError,
)
from aios_kernel.context.compiler import (
    CandidateChunk,
    CompiledContext,
    ContextChunk,
    ContextCompiler,
    DefaultContextCompiler,
    StubSourceProvider,
    WordTokenizer,
)
from aios_kernel.context.models import (
    ContextSource,
    MAX_CONTEXT_TOKENS,
    TaskDescriptor,
)
from aios_kernel.context.knowledge import (
    Document,
    DocumentChunk,
    Knowledge,
    chunk_text,
    cosine,
    hash_embed,
)

__all__ = [
    "DEFAULT_TTL",
    "WorkingMemoryEntry",
    "WorkingMemoryService",
    "MIN_RETENTION_DAYS",
    "LongTermEntry",
    "LongTermMemoryService",
    "RetentionPolicyError",
    "CompiledContext",
    "ContextChunk",
    "ContextCompiler",
    "ContextSource",
    "MAX_CONTEXT_TOKENS",
    "TaskDescriptor",
    "Document",
    "DocumentChunk",
    "Knowledge",
    "chunk_text",
    "cosine",
    "hash_embed",
]





