---
id: skill/codex-supervisor-pattern
version: 1.0.0
title: Codex Supervisor Pattern
description: |
  After Codex spawn_agent assigns tasks, Codex must independently verify each
  card's evidence before marking Verified. Each card has: (a) main evidence.md,
  (b) preflight_output.txt, (c) git commit SHA, (d) pytest output, (e) Forbidden
  Files 0 issues. Codex re-runs ≥3 evidence steps before signing off.

  This pattern prevents "false completion" where an agent claims success
  without actual evidence. It mirrors the Verifier's role but operates at
  the supervisor-of-supervisors level.

promoted_at: 2026-10-08
promoted_from: T0009 evolution_candidate E002
evidence_source: D:\AIOS\aios_tasks\aios_vnext\evidence\T0035__20261008-115800.md (PID proof)

# Usage Example
```python
def codex_verify_card(card_id: str):
    evidence_path = f"D:\\AIOS\\aios_tasks\\aios_vnext\\evidence\\{card_id}__<ts>.md"
    preflight_path = f"D:\\AIOS\\aios_tasks\\aios_vnext\\evidence\\preflight_{card_id}_<ts>.txt"
    # Read both files
    ev = read(evidence_path)
    pf = read(preflight_path)
    # Cross-check 5 elements present
    assert all(elem in ev for elem in ["Scope", "Evidence Requirements", "Exit Criteria"])
    assert "CLEAN" in pf and "0 issues" in pf
    # git log
    assert subprocess.run(["git", "log", "--oneline", "-1"], cwd="D:\\AIOS\\kernel").returncode == 0
    return "Verified"
```

# Test Method
1. Spawn agent to do a card
2. Codex reads evidence file
3. Codex re-runs ≥3 evidence steps
4. Codex signs off only after all 5 elements pass
