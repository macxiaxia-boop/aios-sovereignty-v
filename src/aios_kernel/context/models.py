"""models.py - Phase B B004 Context Compiler data models.

Defines the public data contracts for the Context Compiler:

  - ContextSource:  the 4 canonical sources (working_memory / long_term_memory
                    / knowledge / skill_registry) — fixed enum so the
                    4-source priority contract is statically checkable.
  - ContextChunk:   one item the compiler picked from a source.
  - CompiledContext: the result returned to callers (LLM prompt builder etc).
  - TaskDescriptor:  the input the caller hands to ContextCompiler.compile().

Design contract (B004 spec §Scope items 1 + 2):
  - total_tokens MUST be <= 4096 (enforced by validator).
  - relevance MUST be in [0.0, 1.0] (enforced by validator).
  - tokens MUST be >= 0 (enforced by validator).
  - The `truncated` flag is True iff the last accepted chunk was cut short
    to fit the budget; the cut content is preserved in the chunk's
    `content` field (truncated at a word boundary when possible).

Note: B002 (WorkingMemoryService) and B003 (LongTermMemoryService) are
still in flight at the time B004 is being implemented. B004 only depends
on the SourceProvider Protocol surface (defined in compiler.py), not on
either service class directly. The 4 stub providers in compiler.py
mimic the future B002/B003 + B005/B006 surfaces; once those are
Verified, real providers can be plugged in via the Protocol with no
changes to this module.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Hard upper bound on total tokens for any compiled context.
# B004 spec §Scope item 1: total_tokens <= 4096.
MAX_CONTEXT_TOKENS: int = 4096


class ContextSource(str, Enum):
    """The 4 canonical context sources (B004 spec §Scope item 2).

    Source priority contract (B004 spec §Evidence Requirements):
        working_memory > long_term_memory > knowledge > skill_registry
    The compiler uses this enum's declaration order as a tie-breaker
    when two candidates have equal relevance scores.

    NOTE: declaring the members in priority order is intentional and
    load-bearing — the compiler relies on enum member order to keep
    the priority contract static.
    """

    WORKING_MEMORY = "working_memory"          # highest priority (1)
    LONG_TERM_MEMORY = "long_term_memory"      # priority 2
    KNOWLEDGE = "knowledge"                    # priority 3
    SKILL_REGISTRY = "skill_registry"          # lowest priority (4)

    @property
    def priority(self) -> int:
        """Lower number = higher priority (used as tie-breaker)."""
        order = {
            ContextSource.WORKING_MEMORY: 1,
            ContextSource.LONG_TERM_MEMORY: 2,
            ContextSource.KNOWLEDGE: 3,
            ContextSource.SKILL_REGISTRY: 4,
        }
        return order[self]


class ContextChunk(BaseModel):
    """A single piece of context chosen by the compiler.

    Carries the original `content` (which may be a truncated copy of the
    source material — see `truncated` flag on CompiledContext), the
    source it came from, a normalised relevance score in [0, 1], the
    token cost the compiler paid for it, and an optional back-link to
    the source Evidence row (e.g. a T0009 growth-capability evidence
    the chunk was derived from).
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    source: ContextSource = Field(
        ...,
        description="Where this chunk came from (one of the 4 canonical sources).",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=200_000,
        description="Text payload. May be a truncation of the source content.",
    )
    relevance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalised relevance score in [0, 1]. Tie-broken by source priority.",
    )
    tokens: int = Field(
        ...,
        ge=0,
        description="Token cost the compiler paid for this chunk.",
    )
    evidence_id: str | None = Field(
        default=None,
        description="Back-link to the source Evidence row (UUID4), if any.",
    )

    @field_validator("content")
    @classmethod
    def _strip_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content cannot be empty after strip")
        return v


class CompiledContext(BaseModel):
    """The compiler's output — ready to be injected into an LLM prompt.

    Invariants:
      - total_tokens == sum(c.tokens for c in compiled)  (compiler sets this)
      - total_tokens <= MAX_CONTEXT_TOKENS                (4096)
      - truncated is True iff the last chunk had to be cut short

    The elapsed_ms field is set by the compiler at build time so the
    caller can spot slow compiles (e.g. > 200ms) without instrumenting
    the code.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    task_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="The task this context was compiled for.",
    )
    compiled: list[ContextChunk] = Field(
        default_factory=list,
        description="Chunks in priority order (highest priority first).",
    )
    total_tokens: int = Field(
        default=0,
        ge=0,
        le=MAX_CONTEXT_TOKENS,
        description=f"Sum of chunk tokens; must be <= {MAX_CONTEXT_TOKENS}.",
    )
    truncated: bool = Field(
        default=False,
        description="True iff the last accepted chunk had to be cut to fit the budget.",
    )
    elapsed_ms: int = Field(
        default=0,
        ge=0,
        description="Wall-clock compile time in milliseconds (compiler-measured).",
    )
    cache_hit: bool = Field(
        default=False,
        description="True if this result was served from the in-memory cache.",
    )
    built_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the result was assembled (tz-aware).",
    )

    @model_validator(mode="after")
    def _check_invariants(self):
        if self.total_tokens > MAX_CONTEXT_TOKENS:
            raise ValueError(
                f"total_tokens={self.total_tokens} exceeds MAX_CONTEXT_TOKENS={MAX_CONTEXT_TOKENS}"
            )
        if self.cache_hit and self.compiled:
            # Sanity: a cache hit is allowed to have an empty compiled list
            # only if total_tokens == 0; non-zero total_tokens implies at
            # least one chunk was present originally.
            pass
        return self

    # ---------- helpers -----------------------------------------------------

    def render(self, separator: str = "\n\n") -> str:
        """Render the compiled chunks as a single string (prompt-ready).

        Each chunk is prefixed with `[source=<source>] ` so the LLM can
        tell where each block came from. The separator defaults to a
        blank line.
        """
        if not self.compiled:
            return ""
        parts = []
        for c in self.compiled:
            parts.append(f"[source={c.source.value}] {c.content}")
        return separator.join(parts)


class TaskDescriptor(BaseModel):
    """The input the caller hands to ContextCompiler.compile().

    Carries enough metadata for the compiler's relevance scorer:
      - task_id: stable identifier (also the cache key)
      - title + description: free-form text used for keyword overlap
      - tags: explicit tag list that boosts candidates with matching tags
      - explicit_evidence_ids: hint list — chunks that back-link to any
        of these get a relevance bump (so a T0009 evidence tag can
        pre-promote its dependent chunks).
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    task_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Stable task id (also the cache key).",
    )
    title: str = Field(
        default="",
        max_length=500,
        description="Short task title (used for keyword overlap).",
    )
    description: str = Field(
        default="",
        max_length=10_000,
        description="Free-form task description (used for keyword overlap).",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Explicit tag list (used for relevance boost).",
    )
    explicit_evidence_ids: list[str] = Field(
        default_factory=list,
        description="Optional evidence-id hint list (chunks with matching back-links are boosted).",
    )
    max_tokens: int = Field(
        default=MAX_CONTEXT_TOKENS,
        ge=1,
        le=MAX_CONTEXT_TOKENS,
        description=f"Token budget for the compile; clamped to <= {MAX_CONTEXT_TOKENS}.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form metadata (not used by the compiler, passed through).",
    )


__all__ = [
    "MAX_CONTEXT_TOKENS",
    "ContextSource",
    "ContextChunk",
    "CompiledContext",
    "TaskDescriptor",
]
