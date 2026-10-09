---
id: skill/5-element-evidence-pattern
version: 1.0.0
title: 5-Element Evidence Pattern
description: |
  Every Verified card must contain exactly 5 evidence elements:
    (a) main evidence.md (covering scope, evidence requirements, exit criteria)
    (b) preflight_output.txt (CLEAN, 0 issues)
    (c) git commit SHA (in kernel or operator repo)
    (d) pytest output (unit + integration)
    (e) Forbidden Files 0 issues (explicit count)

  Missing any 1 of 5 → card not Verified. This pattern prevents "looks done"
  false positives common in unsupervised execution.

promoted_at: 2026-10-08
promoted_from: T0009 evolution_candidate E004
evidence_source: D:\AIOS\aios_tasks\aios_vnext\evidence\T0034__20261008-114500.md
template: D:\AIOS\aios_tasks\aios_vnext\evidence\T*.md

# Usage Example
```python
def verify_5_elements(card_id: str) -> bool:
    base = f"D:\\AIOS\\aios_tasks\\aios_vnext\\evidence\\{card_id}"
    return all([
        Path(f"{base}__<ts>.md").exists(),         # main evidence
        Path(f"{base}_preflight.txt").exists(),    # preflight
        # git commit (call git CLI)
        subprocess.run(["git", "log", "--oneline", "-1"], cwd="D:\\AIOS\\kernel").returncode == 0,
        # pytest (call pytest)
        subprocess.run(["pytest", "-q"], cwd="D:\\AIOS\\kernel").returncode == 0,
        # Forbidden count
        "0 issues" in Path(f"{base}_preflight.txt").read_text(),
    ])
```

# Test Method
1. Pick any Verified card from INDEX
2. Verify all 5 elements exist
3. If any missing → card should not be Verified (catch inconsistency)
