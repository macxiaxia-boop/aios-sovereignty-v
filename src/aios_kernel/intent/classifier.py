"""classifier.py - F002 IntentType enum.

Per F002 card §1 Scope 1 (parser signature reference) and §3 test cases,
we classify user text into one of 6 types:

    COMMAND     - "做X", "建一个营销活动"
    STATEMENT   - "我们正在Y", "我需要..."
    QUESTION    - "怎么Z", "为什么..."
    CONSTRAINED - "在A条件下做B"
    TRADEOFF    - "宁可C不要D"
    UNKNOWN     - cannot classify

This module owns ONLY the enum. The matching regex patterns live in
rules.py. IntentParser.parse() composes the classifier with rules + LLM
adapter to produce a GoalContract.
"""
from __future__ import annotations

from enum import Enum


class IntentType(str, Enum):
    """The 5 (+1 UNKNOWN) canonical user-text categories."""

    COMMAND = "command"          # "建一个营销活动"
    STATEMENT = "statement"      # "我需要把今天的工作收尾"
    QUESTION = "question"        # "怎么让 AIOS 知道用户的目标"
    CONSTRAINED = "constrained"  # "在 D:/AIOS 内 不要改 verifier"
    TRADEOFF = "tradeoff"        # "宁可慢 不要出错"
    UNKNOWN = "unknown"          # cannot classify (rule + LLM both fail)


__all__ = ["IntentType"]