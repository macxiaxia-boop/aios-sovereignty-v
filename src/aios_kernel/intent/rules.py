"""rules.py - F002 regex patterns + rule-based extractors.

Per F002 card §Scope 1, this module owns:

    CONSTRAINT_PATTERNS  - regex + type pairs to extract known_constraints
    TRADEOFF_PATTERNS    - regex + type pairs to extract approved_tradeoffs
    INTENT_CLASSIFIER    - intent_type -> [regex] to classify user text

Public helpers:

    extract_constraints(text) -> list[Constraint]
    extract_tradeoffs(text)   -> list[Tradeoff]
    classify_by_rules(text)   -> IntentType   (UNKNOWN if no pattern matches)

Design contract:
    - Pure regex; no LLM. Pattern list is data-driven so F002 tests can
      assert each pattern hits its labelled input.
    - Patterns are intentionally loose (Chinese-first, English-friendly).
      Tight patterns would miss too many real inputs.
    - Order matters within INTENT_CLASSIFIER: first match wins. TRADEOFF
      and CONSTRAINED are tested BEFORE the COMMAND/STATEMENT/QUESTION
      buckets because they are more specific (rare false positives).
"""
from __future__ import annotations

import re
from typing import Any

from aios_kernel.intent.classifier import IntentType


# ---------------------------------------------------------------------------
# Constraint patterns (card §Scope 1)
# ---------------------------------------------------------------------------
# Each tuple is (compiled regex, constraint_type). The capture group #1 is
# the user-facing value; we stuff it into Constraint.value verbatim.

CONSTRAINT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # "不要/禁止/避免 X" — forbid a path or an action
    (re.compile(r"(?:不要|禁止|避免)[\s]*(.{2,40})"), "scope"),
    # "预算 ≤500 / 预算不超 500 / 预算 500" — budget cap (CNY)
    (re.compile(r"预算\s*[≤不超]?\s*(\d+(?:\.\d+)?)"), "budget"),
    # "30 分钟 / 2 小时 / 1 天 / 5 秒 / 5 min / 2 h / 1 d / 3 s"
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:分钟|min|分钟钟|小时|h|天|d|秒|s)", re.IGNORECASE), "timeout"),
    # "尽快 / 紧急 / 马上" — high-priority tag (no value)
    (re.compile(r"(?:尽快|紧急|马上)"), "priority_high"),
]


# ---------------------------------------------------------------------------
# Tradeoff patterns (card §Scope 1)
# ---------------------------------------------------------------------------

TRADEOFF_PATTERNS: list[tuple[re.Pattern, str]] = [
    # "宁可/宁愿/可以 X 不/不要 Y" — explicit approved tradeoff
    (re.compile(r"(?:宁可|宁愿|可以)[^。,;!?\n]{1,40}(?:不|不要)[^。,;!?\n]{1,40}"), "approved_tradeoff"),
    # "代价/成本 X 是/为 Y" — cost-explicit (still a tradeoff: user names cost)
    (re.compile(r"(?:代价|成本)[^。,;!?\n]{1,40}(?:是|为)[^。,;!?\n]{1,40}"), "cost_explicit"),
    # "可以 X 换/换取/以获得 Y" — acceptable tradeoff (positive form)
    (re.compile(r"可以[^。,;!?\n]{1,40}(?:换|换取|换得|以获得)[^。,;!?\n]{1,40}"), "approved_tradeoff"),
    # "X 牺牲 Y" — user names a sacrifice (positive: user accepts it)
    (re.compile(r"[^。,;!?\n]{1,40}牺牲[^。,;!?\n]{1,40}"), "approved_tradeoff"),
]


# ---------------------------------------------------------------------------
# Intent classification patterns (card §Scope 1)
# ---------------------------------------------------------------------------
# IMPORTANT: more specific patterns MUST appear before more general ones
# in the iteration order. classify_by_rules() returns the first hit.

INTENT_CLASSIFIER: dict[IntentType, list[re.Pattern]] = {
    # TRADEOFF first: more-specific patterns win
    IntentType.TRADEOFF: [
        # "宁可/宁愿 X 不/不要 Y"
        re.compile(r"(?:宁可|宁愿)[^。,;!?\n]{0,40}(?:不|不要)[^。,;!?\n]{0,40}"),
        # "可以 X 换/换取/以获得 Y" (acceptable tradeoff)
        re.compile(r"可以[^。,;!?\n]{1,40}(?:换|换取|换得|以获得)[^。,;!?\n]{0,40}"),
        # "X 牺牲 Y" (user names a sacrifice)
        re.compile(r"[^。,;!?\n]{1,40}牺牲[^。,;!?\n]{1,40}"),
        # bare "宁可/宁愿 X" preference (loose)
        re.compile(r"(?:宁可|宁愿)[^。,;!?\n]{1,40}"),
    ],
    # CONSTRAINED: location word + verb; OR budget/timeout prefix + verb
    IntentType.CONSTRAINED: [
        # "在 X 下/里/上/中/内/前提下/情况下/范围内" + verb
        re.compile(r"在[^。,;!?\n]{2,50}(?:下|里|上|中|内|前提下|情况下|范围之内|范围内|之内)[^。,;!?\n]{0,15}(?:做|写|跑|查|建|删|改|修|执行|运行|启动|停止|完成)"),
        # "在不修改 X" + verb
        re.compile(r"在不[^。,;!?\n]{0,30}?[^。,;!?\n]{0,15}(?:做|写|跑|查|建|删|改|修|执行|运行|启动|停止|完成)"),
        # bare "在 X" + verb (no location word required)
        re.compile(r"在[^。,;!?\n]{2,50}[^。,;!?\n]{0,15}(?:建|写|做|跑|查|删|改|修|执行|运行|启动|停止|完成)"),
        # "<budget|timeout|不要> + verb" (constraint-prefix pattern)
        re.compile(r"(?:预算\s*[≤不超]?\s*\d+(?:\.\d+)?(?:\s*元)?|\d+\s*(?:分钟|min|小时|天|秒|h|d|s)|不要|禁止)\s*[^。,;!?\n]{0,30}(?:做|写|建|跑|查|删|改|修|执行|运行|启动|停止|完成)"),
    ],
    # QUESTION: interrogative words
    IntentType.QUESTION: [
        re.compile(r"(?:怎么|为什么|什么|哪个|哪里)[^。,;!?\n]{0,8}(?:做|办|解决|选)?"),
    ],
    # COMMAND: starts with imperative verb (optionally 立即/马上 prefix)
    IntentType.COMMAND: [
        # starts with imperative verb
        re.compile(r"^(?:做|写|建|修|删|改|跑|查|看|打开|关闭|启动|停止|执行|运行|创建|删除|修改)[^。,;!?\n]{0,80}"),
        # "立即/马上 停/关闭/启动 ..."
        re.compile(r"^(?:立即|马上)\s*(?:停|关|开|启动|停止|关闭|做|写|建|查|跑)[^。,;!?\n]{0,80}"),
    ],
    # STATEMENT: starts with "当前/现在/我/我们" + need/want/etc.
    IntentType.STATEMENT: [
        re.compile(r"^(?:当前|现在|我|我们)[^。,;!?\n]{0,15}(?:需要|想|打算|正在|要|希望)"),
    ],
}


def classify_by_rules(text: str) -> IntentType:
    """Return the first matching IntentType, or UNKNOWN if none match.

    Order: TRADEOFF > CONSTRAINED > QUESTION > COMMAND > STATEMENT.
    """
    if not text or not text.strip():
        return IntentType.UNKNOWN
    for intent_type, patterns in INTENT_CLASSIFIER.items():
        for pat in patterns:
            if pat.search(text):
                return intent_type
    return IntentType.UNKNOWN


def extract_constraints(text: str) -> list[dict[str, Any]]:
    """Run CONSTRAINT_PATTERNS against text and return raw constraint dicts.

    Returned shape: ``[{"type": <str>, "value": <str>, "rationale": <str>}, ...]``
    Suitable for ``Constraint(**d)`` once we know ``type`` is one of the
    five Constraint.type literals (the parser maps local ``scope`` etc.
    to the Pydantic enum below).
    """
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()  # (type, value) dedup
    for pat, ctype in CONSTRAINT_PATTERNS:
        for m in pat.finditer(text):
            if m.lastindex and m.group(1):
                value = m.group(1).strip().rstrip("。，,. ")
            else:
                value = ""  # priority_high / no-value matches
            key = (ctype, value)
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "type": ctype,
                "value": value,
                "rationale": f"rule pattern matched: {pat.pattern}",
            })
    return found


def extract_tradeoffs(text: str) -> list[dict[str, Any]]:
    """Run TRADEOFF_PATTERNS against text and return raw tradeoff dicts.

    Returned shape: ``[{"type": <str>, "decision": <str>, "cost": <str>,
                       "benefit": <str>, "approved_by": "user"}, ...]``
    """
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pat, ttype in TRADEOFF_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(0).strip()
            if raw in seen:
                continue
            seen.add(raw)
            decision, cost = _split_tradeoff(raw)
            found.append({
                "type": ttype,
                "decision": decision,
                "cost": cost,
                "benefit": "implicit (user stated)",
                "approved_by": "user",
                "_raw": raw,
            })
    return found


def _split_tradeoff(raw: str) -> tuple[str, str]:
    """Split a raw tradeoff match into (decision, cost).

    Heuristic:
      - "宁可/宁愿 X 不/不要 Y"  →  decision = X (the kept thing),
                                     cost = Y (the sacrificed thing)
      - "代价/成本 X 是/为 Y"    →  decision = Y, cost = X

    Falls back to (raw, "") if the split is ambiguous.
    """
    if any(kw in raw for kw in ("宁可", "宁愿", "可以")):
        for sep in ("不要", "不"):
            if sep in raw:
                head, _, tail = raw.partition(sep)
                # strip leading conjunction from head
                for kw in ("宁可", "宁愿", "可以"):
                    head = head.replace(kw, "", 1)
                return head.strip(" ，,。."), (sep + tail).strip(" ，,。.")
        return raw, ""
    elif any(kw in raw for kw in ("代价", "成本")):
        for sep in ("是", "为"):
            if sep in raw:
                head, _, tail = raw.partition(sep)
                return tail.strip(" ，,。."), head.strip(" ，,。.")
        return raw, ""
    return raw, ""


__all__ = [
    "CONSTRAINT_PATTERNS",
    "TRADEOFF_PATTERNS",
    "INTENT_CLASSIFIER",
    "classify_by_rules",
    "extract_constraints",
    "extract_tradeoffs",
]