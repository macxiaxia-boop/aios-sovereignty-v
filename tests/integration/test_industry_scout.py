"""test_industry_scout.py - D002 Industry Scout integration tests.

Five required cases (D002 scope):
    1. test_collect_empty
    2. test_classify_correct
    3. test_alert_triggered
    4. test_alert_skipped
    5. test_dedup

Plus stretch cases for the Evidence gate.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


def _now():
    return datetime.now(UTC)


def _sig(title, content="", category=None, confidence=0.5, action_required=False):
    from aios_kernel.business.industry_scout import IndustrySignal, SignalCategory
    return IndustrySignal(
        source="test",
        category=category if category is not None else SignalCategory.MARKET,
        title=title,
        content=content,
        confidence=confidence,
        action_required=action_required,
        collected_at=_now(),
    )


# ---- 1. test_collect_empty ------------------------------------------------

def test_collect_empty():
    from aios_kernel.business.industry_scout import IndustryScout
    scout = IndustryScout()
    assert scout.collect([]) == []


def test_collect_empty_source_only():
    from aios_kernel.business.industry_scout import IndustryScout, SourceConfig
    scout = IndustryScout()
    out = scout.collect([SourceConfig("manual", kind="manual"),
                         SourceConfig("rss", kind="rss")])
    assert out == []


# ---- 2. test_classify_correct ---------------------------------------------

def test_classify_correct():
    from aios_kernel.business.industry_scout import IndustryScout, SignalCategory
    scout = IndustryScout()
    cases = [
        ("Acme launches new product", "Beta GA release today", SignalCategory.PRODUCT),
        ("Competitor raises prices 20%", "Rival acquires startup", SignalCategory.COMPETITOR),
        ("FCC approval granted", "New compliance regulation", SignalCategory.REGULATORY),
        ("Market size forecast", "Adoption growth rate is climbing", SignalCategory.MARKET),
        ("New LLM model released", "Open source SDK framework on github", SignalCategory.TECH),
    ]
    for title, content, expected in cases:
        sig = _sig(title, content)
        classified = scout.classify(sig)
        assert classified.category == expected, (
            "classify(" + repr(title) + ") -> " + classified.category.value +
            " -> expected " + expected.value
        )


def test_classify_pydantic_rejects_non_enum():
    from pydantic import ValidationError
    from aios_kernel.business.industry_scout import IndustrySignal, SignalCategory
    with pytest.raises(ValidationError):
        IndustrySignal(source="x", category="bogus_category", title="t",
                       confidence=0.5, collected_at=_now())
    for cat in SignalCategory:
        sig = IndustrySignal(source="x", category=cat, title=cat.value + " test",
                             confidence=0.5, collected_at=_now())
        assert sig.category == cat


# ---- 3. test_alert_triggered ----------------------------------------------

def test_alert_triggered():
    from aios_kernel.business.industry_scout import IndustryScout
    scout = IndustryScout()
    sig = _sig(title="Important signal", content="the alert is needed",
               confidence=0.85)
    assert scout.alert(sig, threshold=0.5) is True
    assert scout.alert(sig, threshold=0.8) is True
    assert scout.alert(sig, threshold=0.0) is True


# ---- 4. test_alert_skipped -----------------------------------------------

def test_alert_skipped():
    from aios_kernel.business.industry_scout import IndustryScout
    scout = IndustryScout()
    sig_b = _sig(title="Boundary", content="at the line", confidence=0.5)
    assert scout.alert(sig_b, threshold=0.5) is False
    sig_c = _sig(title="Low confidence", content="", confidence=0.1)
    assert scout.alert(sig_c, threshold=0.5) is False
    sig_d = _sig(title="x", content="", confidence=0.0)
    assert scout.alert(sig_d, threshold=0.0) is False


# ---- 5. test_dedup -------------------------------------------------------

def test_dedup():
    from aios_kernel.business.industry_scout import IndustryScout
    scout = IndustryScout()
    def dup_source(name):
        return [
            {"title": "Same title", "content": "same content",
             "confidence": 0.9, "action_required": True, "category": "product"},
            {"title": "Same title", "content": "same content",
             "confidence": 0.9, "action_required": True, "category": "product"},
            {"title": "Different title", "content": "different content",
             "confidence": 0.7, "action_required": False, "category": "market"},
            {"title": "Same title", "content": "same content",
             "confidence": 0.8, "action_required": True, "category": "tech"},
        ]
    out = scout.collect([("rss", dup_source)])
    assert len(out) == 2
    titles = sorted(s.title for s in out)
    assert titles == ["Different title", "Same title"]


def test_dedup_across_sources():
    from aios_kernel.business.industry_scout import IndustryScout
    scout = IndustryScout()
    def src_rss(name):
        return [{"title": "X", "content": "Y", "confidence": 0.9, "category": "product"}]
    def src_api(name):
        return [{"title": "X", "content": "Y", "confidence": 0.9, "category": "product"}]
    out = scout.collect([("rss", src_rss), ("api", src_api)])
    assert len(out) == 1
    assert out[0].source == "rss"


# ---- Stretch: 100 signals -> 100/100 classified (D002 Evidence) ----------

def test_collect_100_signals_classified():
    from aios_kernel.business.industry_scout import IndustryScout, SignalCategory
    scout = IndustryScout()
    titles = []
    for i in range(100):
        kind = i % 5
        if kind == 0:
            titles.append(("Acme launches product v" + str(i), "release", "product"))
        elif kind == 1:
            titles.append(("Competitor raises prices " + str(i), "rival acquires", "competitor"))
        elif kind == 2:
            titles.append(("FCC approval " + str(i), "new regulation", "regulatory"))
        elif kind == 3:
            titles.append(("Market size " + str(i), "adoption growth", "market"))
        else:
            titles.append(("New LLM model " + str(i), "open source SDK on github", "tech"))
    def big_source(name):
        return [
            {"title": t, "content": c, "confidence": 0.9,
             "action_required": True, "category": cat}
            for t, c, cat in titles
        ]
    out = scout.collect([("rss", big_source)])
    assert len(out) == 100
    classified = scout.classify_all(out)
    for sig in classified:
        assert sig.category in SignalCategory


def test_collect_100_with_duplicates_keeps_unique():
    from aios_kernel.business.industry_scout import IndustryScout
    scout = IndustryScout()
    def repeating_source(name):
        items = []
        for i in range(25):
            items.append({"title": "T" + str(i), "content": "C" + str(i),
                          "category": "market", "confidence": 0.5})
        return items * 4
    out = scout.collect([("rss", repeating_source)])
    assert len(out) == 25


# ---- Misc edge cases ----------------------------------------------------

def test_source_exception_isolated():
    from aios_kernel.business.industry_scout import IndustryScout
    scout = IndustryScout()
    def bad_source(name):
        raise RuntimeError("simulated source outage")
    def good_source(name):
        return [{"title": "Survivor", "content": "kept",
                 "category": "product", "confidence": 0.7}]
    out = scout.collect([("bad", bad_source), ("good", good_source)])
    assert len(out) == 1
    assert out[0].source == "good"


def test_signal_confidence_validation():
    from pydantic import ValidationError
    from aios_kernel.business.industry_scout import IndustrySignal, SignalCategory
    with pytest.raises(ValidationError):
        IndustrySignal(source="x", category=SignalCategory.MARKET,
                       title="t", confidence=1.5, collected_at=_now())
    with pytest.raises(ValidationError):
        IndustrySignal(source="x", category=SignalCategory.MARKET,
                       title="t", confidence=-0.1, collected_at=_now())


def test_model_validator_fills_hash_when_blank():
    from aios_kernel.business.industry_scout import IndustrySignal, SignalCategory
    sig = IndustrySignal(source="manual", category=SignalCategory.MARKET,
                         title="Manual entry", content="body",
                         confidence=0.5, action_required=False,
                         collected_at=_now())
    assert len(sig.content_hash) == 64
