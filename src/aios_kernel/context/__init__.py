"""__init__.py - aios_kernel.context (Phase B B002 Working Memory + B004 Context Compiler).

Public surface:

  Context Compiler (B004) — token-efficient context assembly from 4 sources:
    - MAX_CONTEXT_TOKENS: hard upper bound (4096)
    - ContextSource: enum of the 4 canonical sources
    - ContextChunk: one compiled chunk
    - CompiledContext: the compiler's output (LLM-prompt-ready)
    - TaskDescriptor: the input the caller hands to compile()
    - ContextCompiler: Protocol interface
    - DefaultContextCompiler: reference implementation
    - SourceProvider: Protocol for one source's collector
    - StubSourceProvider: deterministic in-memory provider (used as
      placeholder until B002/B003/B005/B006 are wired in)
    - WordTokenizer: deterministic word-count tokeniser
    - default_compiler(): convenience factory

  Working Memory (B002) — short-lived per-session state (TTL 24h by default).
    Imported lazily because the B002 work is in flight and its
    persistence layer (WorkingMemoryORM) is not yet in
    aios_kernel.persistence.models. Once B002 is Verified the
    `__getattr__` hook will return the real symbols. If B002 stays
    un-importable, the symbols are set to None and the package still
    works for B004 callers.
"""
from __future__ import annotations

from aios_kernel.context.compiler import (
    CandidateChunk,
    ContextCompiler,
    DefaultContextCompiler,
    SourceProvider,
    StubSourceProvider,
    Tokenizer,
    WordTokenizer,
    default_compiler,
)
from aios_kernel.context.models import (
    MAX_CONTEXT_TOKENS,
    CompiledContext,
    ContextChunk,
    ContextSource,
    TaskDescriptor,
)

# B002 (WorkingMemory) — lazy import. The module imports a persistence
# ORM class that is not yet in the persistence layer; we don't want
# B002's in-flight state to break B004's import chain.
_B002_SYMBOLS = {
    "WorkingMemoryEntry": None,
    "WorkingMemoryService": None,
    "DEFAULT_TTL": None,
}


def __getattr__(name):
    """PEP 562 lazy attribute access.

    The B002 module is imported on first access to any of its symbols
    so a broken B002 import doesn't cascade into B004 import failures.
    """
    if name in _B002_SYMBOLS:
        if _B002_SYMBOLS[name] is None:
            try:
                from aios_kernel.context import working_memory as _wm

                _B002_SYMBOLS["WorkingMemoryEntry"] = _wm.WorkingMemoryEntry
                _B002_SYMBOLS["WorkingMemoryService"] = _wm.WorkingMemoryService
                _B002_SYMBOLS["DEFAULT_TTL"] = _wm.DEFAULT_TTL
            except ImportError as exc:  # pragma: no cover - depends on env
                raise ImportError(
                    f"aios_kernel.context.{name} is not importable; "
                    f"B002 (WorkingMemory) appears to be in flight and its "
                    f"persistence ORM is not yet defined. Underlying error: {exc}"
                ) from exc
        return _B002_SYMBOLS[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # B004 - models
    "MAX_CONTEXT_TOKENS",
    "ContextSource",
    "ContextChunk",
    "CompiledContext",
    "TaskDescriptor",
    # B004 - compiler
    "CandidateChunk",
    "Tokenizer",
    "WordTokenizer",
    "SourceProvider",
    "StubSourceProvider",
    "ContextCompiler",
    "DefaultContextCompiler",
    "default_compiler",
    # B002 (lazy)
    "WorkingMemoryEntry",
    "WorkingMemoryService",
    "DEFAULT_TTL",
]
