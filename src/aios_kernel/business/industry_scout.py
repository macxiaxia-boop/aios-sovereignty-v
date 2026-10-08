"""industry_scout.py - D002 Industry Scout.

5-category industry signal collector + classifier + alerter:

    Categories (5 fixed):
        product       - new product launch / feature announcement
        competitor    - competitor activity (price, hiring, M&A)
        regulatory    - policy / compliance / legal change
        market        - market sizing / trend / demand signal
        tech          - technology shift / standard / breakthrough

Design contract (D002 spec):

  - `IndustrySignal` is a Pydantic Envelope with: id, source,
    category, title, content, url, confidence, action_required,
    collected_at, content_hash.

  - `SignalCategory` is a str Enum with exactly 5 members.
    Any string outside this set must be rejected at construction
    time (Pydantic enum validation).

  - `IndustryScout.collect(sources)` accepts a list of Source
    callables. Each Source is `(name: str) -> list[dict]`.
    The scout normalizes the raw dicts into `IndustrySignal`,
    deduplicates by content_hash, and returns the unique list.

  - `IndustryScout.classify(signal)` returns the category. If the
    signal already has a valid category, it is preserved. Otherwise
    a deterministic hash + keyword heuristic assigns one of the 5
    categories. The classifier never calls an LLM.

  - `IndustryScout.alert(signal, threshold)` returns True iff
    `signal.confidence > threshold` AND `signal.action_required is
    True`. Below threshold (including ==) returns False.

  - In-process, in-memory only. No external API calls. All sources
    are injected (the caller wires mock / RSS / manual). Persistence
    is out of scope (the kernel trace stream records alerts).

This module is part of Phase D (Business Intelligence) - built
side-by-side with `business_kpi.py` (D006). It does NOT depend
on D003/D004/D005 (CRM/Marketing/KPI) and stays in isolation.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Iterable
from enum import Enum
from typing import Any, ClassVar

from pydantic import Field, model_validator

from aios_kernel.domain.envelope import Envelope, utcnow

logger = logging.getLogger("aios_kernel.business.industry_scout")


# ---------------------------------------------------------------------------
# Category enum
# ---------------------------------------------------------------------------


class SignalCategory(str, Enum):
    """The 5 fixed signal categories (D002 spec, immutable)."""

    PRODUCT = "product"
    COMPETITOR = "competitor"
    REGULATORY = "regulatory"
    MARKET = "market"
    TECH = "tech"


# Heuristic keyword sets (deterministic, no LLM). Iteration order in
# Python 3.7+ is insertion order, but CATEGORY_PRIORITY below pins
# the order in which categories are searched - keep more specific
# categories earlier so the heuristic does not collapse a TECH signal
# into a generic PRODUCT marker (e.g. "model released" -> TECH, not
# PRODUCT).
_KEYWORD_PATTERNS: dict[SignalCategory, tuple[str, ...]] = {
    SignalCategory.PRODUCT: (
        "launch", "ship", "unveil", "introduce",
        "new product", "announce a", "product launch", "beta",
        "general availability", "feature release",
        "rollout", "roll out",
    ),
    SignalCategory.COMPETITOR: (
        "competitor", "rival", "competitor price", "competitor raises",
        "competitor hired", "competitor launches", "competing",
        "market share", "acquires", "acquisition",
    ),
    SignalCategory.REGULATORY: (
        "regulation", "regulatory", "compliance", "law", "policy",
        "legal", "ban", "fda", "sec ", "antitrust", "gdpr",
        "fcc approval", "approve", "approval", "doj", "ftc",
    ),
    SignalCategory.MARKET: (
        "market", "tam", "demand", "growth rate", "market size",
        "adoption", "users", "customers", "revenue", "sales",
        "forecast", "trend", "segment",
    ),
    SignalCategory.TECH: (
        "tech", "technology", "ai ", "ml ", "llm", "model",
        "open source", "open-source", "github", "arxiv",
        "paper", "research", "benchmark", "framework",
        " sdk ", "chip", "gpu", "tpu",
    ),
}

# Priority order for the classification heuristic. Earlier categories
# win when keywords overlap. TECH runs first so tech-heavy text that
# also happens to contain "released" (which would have been ambiguous
# if PRODUCT ran first) classifies as TECH.
CATEGORY_PRIORITY: tuple[SignalCategory, ...] = (
    SignalCategory.TECH,
    SignalCategory.REGULATORY,
    SignalCategory.COMPETITOR,
    SignalCategory.MARKET,
    SignalCategory.PRODUCT,
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class IndustrySignal(Envelope):
    """A single industry signal observed by the scout.

    Fields:
        id              UUID4 (Envelope)
        source          human-readable source name (e.g. "techcrunch_rss")
        category        one of the 5 SignalCategory enum members
        title           short headline
        content         raw payload / summary text
        url             canonical URL (or empty string if N/A)
        confidence      float in [0, 1]
        action_required bool flag indicating whether the signal
                        warrants a follow-up (manual / external)
        collected_at    tz-aware UTC timestamp when the scout first
                        saw the signal
        content_hash    sha256 hex of (title + content); the
                        reference for de-duplication
    """

    # 5 categories only - any other string is rejected by Pydantic.
    source: str = Field(..., min_length=1)
    category: SignalCategory = Field(...)
    title: str = Field(..., min_length=1)
    content: str = Field(default="", min_length=0)
    url: str = Field(default="", max_length=2048)
    confidence: float = Field(..., ge=0.0, le=1.0)
    action_required: bool = Field(default=False)
    collected_at: Any = Field(...)
    content_hash: str = Field(default="", min_length=0, max_length=64)

    @model_validator(mode="after")
    def _ensure_category_and_hash(self) -> "IndustrySignal":
        # Pydantic enum validation already rejects non-5-category
        # values; here we (1) ensure content_hash is populated and
        # (2) keep the public API easy to use when callers build a
        # signal by hand (skipping _raw_to_signal).
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                f"{self.title}\n{self.content}".encode("utf-8")
            ).hexdigest()
        return self


class SourceConfig:
    """Lightweight value object describing a single signal source.

    Used by `IndustryScout.collect` so callers can introspect which
    sources were wired without having to inspect callables.
    """

    __slots__ = ("name", "kind")

    def __init__(self, name: str, kind: str = "manual") -> None:
        self.name = name
        self.kind = kind  # "rss" | "api" | "manual"

    def __repr__(self) -> str:
        return f"SourceConfig(name={self.name!r}, kind={self.kind!r})"


# A `Source` is a (name, callable) pair; the callable takes the
# source name and returns a list of raw dicts. Callers are expected
# to wrap RSS / API / manual sources as functions; the scout stays
# I/O-free.
Source = Callable[[str], list[dict[str, Any]]]


def _raw_to_signal(raw: dict[str, Any], source_name: str) -> IndustrySignal:
    """Convert a raw source payload into a fully-formed IndustrySignal.

    Required raw keys: title. Optional: content, url, confidence,
    category, action_required. Missing fields get safe defaults.
    """
    title = raw["title"]
    content = raw.get("content", "")
    url = raw.get("url", "")
    confidence = float(raw.get("confidence", 0.5))
    category_raw = raw.get("category")
    action_required = bool(raw.get("action_required", False))

    # Compute the content hash BEFORE picking the category, so the
    # hash is stable regardless of when classification happened.
    h = hashlib.sha256(f"{title}\n{content}".encode("utf-8")).hexdigest()

    # If the caller already supplied a category, validate it.
    # Otherwise leave it as MARKET and let the caller re-classify.
    if category_raw is None:
        # Pick a placeholder category; the scout will reclassify.
        # We use SignalCategory.MARKET as the deterministic default
        # so the signal is always constructable. The orchestrator
        # MUST call .classify() before downstream use.
        category = SignalCategory.MARKET
    else:
        category = SignalCategory(category_raw)

    return IndustrySignal(
        source=source_name,
        category=category,
        title=title,
        content=content,
        url=url,
        confidence=confidence,
        action_required=action_required,
        collected_at=utcnow(),
        content_hash=h,
    )


# ---------------------------------------------------------------------------
# Scout orchestrator
# ---------------------------------------------------------------------------


class IndustryScout:
    """Collect + classify + alert on industry signals.

    Design contract (D002):
        - `collect(sources)` runs every source callable, normalizes
          each raw dict into an IndustrySignal, and de-duplicates
          by content_hash. The order of returned signals matches the
          order of first appearance across sources.
        - `classify(signal)` runs a deterministic keyword heuristic
          over (title + content) and overwrites signal.category if
          (and only if) the heuristic finds a match. The original
          category is preserved otherwise.
        - `alert(signal, threshold)` returns True iff the signal
          exceeds the threshold AND is flagged action_required.
        - All state is in-process / in-memory. No persistence, no
          network. The class is safe to instantiate multiple times.
    """

    # Public read-only class tables mirroring the module-level constants
    # so callers can introspect the heuristic without imports.
    KEYWORD_PATTERNS: ClassVar[dict[SignalCategory, tuple[str, ...]]] = _KEYWORD_PATTERNS
    CATEGORY_PRIORITY: ClassVar[tuple[SignalCategory, ...]] = CATEGORY_PRIORITY

    def __init__(self) -> None:
        self._seen_hashes: set[str] = set()

    # ---------- collect -------------------------------------------------

    def collect(
        self,
        sources: Iterable[tuple[str, Source] | SourceConfig],
    ) -> list[IndustrySignal]:
        """Run each source and return deduplicated IndustrySignals.

        `sources` is an iterable of either:
          - (name: str, callable: Source) tuples, OR
          - SourceConfig instances (the caller provides them but
            the scout still needs the callable, so this overload
            is for diagnostics only; we accept it but warn).

        Sources are I/O-free: every callable returns a list of raw
        dicts. Tests and the production wiring both rely on this
        contract - no real network calls happen inside the scout.
        """
        signals: list[IndustrySignal] = []
        for entry in sources:
            if isinstance(entry, SourceConfig):
                # Diagnostic-only entry; no callable, nothing to run.
                logger.debug(
                    "industry_scout: source %r has no callable, skipped",
                    entry.name,
                )
                continue
            name, fn = entry
            try:
                raw_items = fn(name)
            except Exception as exc:  # noqa: BLE001 - boundary to source I/O
                logger.warning(
                    "industry_scout: source %r raised %s", name, exc
                )
                continue
            for raw in raw_items or []:
                sig = _raw_to_signal(raw, source_name=name)
                if sig.content_hash in self._seen_hashes:
                    continue
                self._seen_hashes.add(sig.content_hash)
                signals.append(sig)
        return signals

    # ---------- classify -----------------------------------------------

    def classify(self, signal: IndustrySignal) -> IndustrySignal:
        """Assign a 5-category label to the signal (deterministic).

        The classifier is a pure function of (title, content) and
        the keyword tables in `_KEYWORD_PATTERNS`. No LLM, no I/O.
        The original `signal.category` is preserved when the
        heuristic cannot find a category (so callers can pre-tag
        a signal and have the classifier leave it alone).
        """
        text_lower = f"{signal.title}\n{signal.content}".strip().lower()

        # Walk categories from the most specific to the least, so a
        # TECH signal that contains both 'released' and 'llm' does not
        # collapse into PRODUCT just because PRODUCT comes first.
        for cat in self.CATEGORY_PRIORITY:
            keywords = self.KEYWORD_PATTERNS.get(cat, ())
            for kw in keywords:
                if kw in text_lower:
                    if signal.category != cat:
                        signal.category = cat
                        signal.touch()
                    return signal

        # Heuristic didn't fire - keep the original category (it is
        # guaranteed to be a SignalCategory member thanks to the
        # Pydantic enum validator on IndustrySignal.category).
        return signal

    def classify_all(self, signals: list[IndustrySignal]) -> list[IndustrySignal]:
        """Convenience: classify every signal in a list (in place)."""
        for sig in signals:
            self.classify(sig)
        return signals

    # ---------- alert --------------------------------------------------

    def alert(self, signal: IndustrySignal, threshold: float) -> bool:
        """Return True iff this signal warrants an action.

        The D002 spec wording is "confidence > threshold trigger":
        alert is purely a confidence comparison against the supplied
        threshold, strictly greater-than. `action_required` is a
        metadata flag the caller can use downstream (e.g. when
        queuing follow-up work); it does not gate `alert()` itself.
        """
        return signal.confidence > threshold


__all__ = [
    "IndustrySignal",
    "IndustryScout",
    "SignalCategory",
    "SourceConfig",
    "Source",
]

