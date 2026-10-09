---
id: skill/preflight-anti-protocol-explosion
version: 1.0.0
title: Preflight Anti-Protocol-Explosion
description: |
  When spawning sub-agents that create files, automatically run preflight_check.py
  to verify forbidden patterns (protocol_*.md, version_*.md, _r*.py, etc.) are not
  created. FAIL preflight → immediate rollback of any forbidden files.

  This skill enforces the AIOS "system rules AI, not AI rules AI" principle
  at the file creation boundary. Without it, LLMs default to creating new
  numbered protocol files (protocol_1, protocol_2, ...) which dilutes
  the canonical plan.

promoted_at: 2026-10-08
promoted_from: T0009 evolution_candidate E001
evidence_source: D:\AIOS\aios_tasks\aios_vnext\evidence\T0009__20261008-121200.md
kernel_location: D:\AIOS\kernel\tests\sim\mocks\crash_injector.py (sibling: preflight_check.py)

# Usage Example
```python
from aios_kernel.context.preflight_runner import run_preflight
result = run_preflight("D:\AIOS\aios_tasks\aios_vnext")
if result.status == "DIRTY":
    # Rollback forbidden files
    for f in result.forbidden_files:
        os.remove(f)
    raise SkillFailure("preflight failed")
```

# Test Method
1. Try to create `protocol_999.md` → preflight detects → FAIL
2. Verify cleanup happens
3. Verify other files remain intact
