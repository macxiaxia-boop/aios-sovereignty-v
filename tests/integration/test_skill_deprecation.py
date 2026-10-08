"""test_skill_deprecation.py - C007 tests."""
from __future__ import annotations
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock


def test_detect_deprecated_old_skill():
    from aios_kernel.learning.skill_deprecation import SkillDeprecationDetector
    from aios_kernel.learning.skill_usage import SkillUsage
    det = SkillDeprecationDetector()
    # Skill used 60 days ago → deprecated
    old_skill = MagicMock()
    old_skill.last_used_at = datetime.now(UTC) - timedelta(days=60)
    skill_map = {"old_skill": old_skill}
    deps = det.detect_deprecated(skill_map, unused_days=30)
    assert len(deps) == 1
    assert deps[0].skill_id == "old_skill"


def test_detect_recent_skill_not_deprecated():
    from aios_kernel.learning.skill_deprecation import SkillDeprecationDetector
    det = SkillDeprecationDetector()
    recent_skill = MagicMock()
    recent_skill.last_used_at = datetime.now(UTC) - timedelta(days=5)
    skill_map = {"recent": recent_skill}
    deps = det.detect_deprecated(skill_map, unused_days=30)
    assert deps == []


def test_audit_log_present():
    from aios_kernel.learning.skill_deprecation import SkillDeprecationDetector
    det = SkillDeprecationDetector()
    old_skill = MagicMock()
    old_skill.last_used_at = datetime.now(UTC) - timedelta(days=60)
    deps = det.detect_deprecated({"old": old_skill}, unused_days=30)
    assert len(deps[0].audit_log) >= 1


def test_multiple_deprecated():
    from aios_kernel.learning.skill_deprecation import SkillDeprecationDetector
    det = SkillDeprecationDetector()
    skill_map = {}
    for i in range(5):
        s = MagicMock()
        s.last_used_at = datetime.now(UTC) - timedelta(days=60)
        skill_map[f"old_{i}"] = s
    deps = det.detect_deprecated(skill_map, unused_days=30)
    assert len(deps) == 5


def test_format():
    from aios_kernel.learning.skill_deprecation import SkillDeprecationDetector
    det = SkillDeprecationDetector()
    old_skill = MagicMock()
    old_skill.last_used_at = datetime.now(UTC) - timedelta(days=60)
    deps = det.detect_deprecated({"old": old_skill}, unused_days=30)
    d = deps[0]
    assert d.reason != ""
    assert d.unused_days == 30
