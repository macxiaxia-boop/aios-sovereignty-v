---
id: skill/simulation-harness-100task
version: 1.0.0
title: Simulation Harness (100-task + 6 worker + MockClock)
description: |
  100 deterministic mock tasks (5 types × 20, seed=42) + 6 mock workers
  (Success/FakeDone/Crash/Timeout/RetryableFail/PermanentFail) + MockClock
  with time_compression=86400 (1 sec real = 1 day sim) + CrashInjector wrapper
  for kill+restart cycles. Runs full 10 Phase A acceptance criteria in 0.04s.

  Compresses real-world test cycles from weeks to minutes. Phase A 10
  criteria all validated in single e2e run.

promoted_at: 2026-10-08
promoted_from: T0009 evolution_candidate E003
evidence_source: D:\AIOS\aios_tasks\aios_vnext\evidence\T0040__20261008-110751.md
kernel_location: D:\AIOS\kernel\tests\sim\

# Usage Example
```bash
cd D:\AIOS\kernel
python tests/sim/runner.py        # 0.04s, 10/10 criteria PASS
python tests/sim/test_simulation_e2e.py  # 1.04s, 6 e2e checks
```

# Test Method
1. Run `runner.py` → expect criteria_passed=10/10
2. Run `test_simulation_e2e.py` → expect wall<60s
3. Verify preflight CLEAN
