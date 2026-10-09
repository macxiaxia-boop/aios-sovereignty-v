"""llm_adapter.py - F002 LLM adapter Protocol + NullLLMAdapter default.

Per F002 card §Scope 3 (LLM adapter interface, optional injection):

    class LLMAdapter(Protocol):
        def infer_intent(self, user_text, candidates) -> str | None: ...
        def classify_intent(self, user_text) -> IntentType | None: ...

    class NullLLMAdapter:
        # default no-op; rule-only mode
        def infer_intent(self, user_text, candidates): return None
        def classify_intent(self, user_text): return None

F002 hard rule: do NOT call any real LLM (no OpenAI / Anthropic / etc.).
NullLLMAdapter is the canonical default. Downstream integrations (Phase G+)
can plug in a real adapter without changing IntentParser's API.

Why a Protocol (not ABC): Protocol keeps the adapter duck-typed; callers
inject any object that has the two methods. Tests can pass a MockLLMAdapter
without inheriting from a base class.
"""
from __future__ import annotations

from typing import Protocol

from aios_kernel.intent.classifier import IntentType


class LLMAdapter(Protocol):
    """Optional LLM fallback interface (rule + LLM hybrid).

    Methods return ``None`` when the adapter cannot produce a confident
    answer; the parser then falls back to rule-only output.
    """

    def infer_intent(self, user_text: str, candidates: list[str]) -> str | None:
        """Pick the best ``inferred_intent`` from a list of candidates.

        Args:
            user_text: raw user input.
            candidates: rule-suggested intent candidates (e.g. "build a
                marketing campaign", "execute a stop command").

        Returns:
            The best candidate, or ``None`` if the adapter abstains.
        """
        ...

    def classify_intent(self, user_text: str) -> IntentType | None:
        """Re-classify the text if rules are inconclusive.

        Returns:
            An :class:`IntentType` value, or ``None`` if the adapter abstains.
        """
        ...


class NullLLMAdapter:
    """Default no-op adapter (rule-only mode).

    Both methods return ``None`` so the parser falls back to deterministic
    rule output. This is the **default** — IntentParser() with no args
    uses this adapter, so F002 ships with **zero external LLM dependency**.

    Tests can substitute a recording mock by passing a custom ``llm_adapter``
    to IntentParser.__init__.
    """

    __slots__ = ("calls",)

    def __init__(self) -> None:
        # Optional: lets tests assert that the parser tried the adapter
        # at least once before falling back. Not required by F002 spec.
        self.calls: list[tuple[str, tuple]] = []

    def infer_intent(self, user_text: str, candidates: list[str]) -> str | None:
        self.calls.append(("infer_intent", (user_text, tuple(candidates))))
        return None

    def classify_intent(self, user_text: str) -> IntentType | None:
        self.calls.append(("classify_intent", (user_text,)))
        return None


__all__ = ["LLMAdapter", "NullLLMAdapter"]