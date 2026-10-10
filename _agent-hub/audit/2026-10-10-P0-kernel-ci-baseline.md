# P0 kernel CI baseline - 2026-10-10

## Environment
- cwd: D:\AIOS\kernel
- PYTHONPATH=D:\AIOS\kernel
- fastapi: requested 0.143.0 installed (pip shows current 0.140.13 was prior)
- uvicorn: requested 0.54.0 installed (pip shows current 0.51.0 was prior)
- pip dep warnings (non-blocking):
  - aios-kernel needs psycopg/binary, pydantic-settings, temporalio (NOT critical for current tests)
  - hermes-agent openai ver conflict (NOT in test path)

## Critical 3 files (separately)
test_crash_recovery (10) + test_long_term_memory (5) + test_verifier_independent (7) = **22/22 PASS in 59.60s**

```
test_crash_recovery (10):       all 10 PASS (CR1..CR10, no FLAKE, no FAIL)
test_long_term_memory (5):      all 5 PASS
test_verifier_independent (7):  all 7 PASS
```

## Full integration suite
**179/179 PASSED in 69.36s (1:09)**

## Comparison
| Phase | Result | Time |
|-------|--------|------|
| Round 8 | 22/23 (1 FLAKE) | reported |
| Round 10 latest | 23/24 | reported |
| **P0 baseline (this)** | **22 critical + 179 full INTEGRATION** | **59.60s + 69.36s** |

## PASS/FAIL summary
- test_crash_recovery.py        10/10 PASS ✓
- test_long_term_memory.py       5/5  PASS ✓
- test_verifier_independent.py   7/7  PASS ✓
- All 179 integration tests PASSED

## Notes
- No FAIL anywhere
- No FLAKE in this run (Round 8 was 22/23 with 1 FLAKE pre-existing; today's run does not reproduce flake)
- fastapi/uvicorn version bump from 0.140.13→0.143.0 and 0.51.0→0.54.0: didn't break anything

## Files
- D:\AIOS\_agent-hub\audit\_p0_critical_3.log (22 tests, 59.6s)
- D:\AIOS\_agent-hub\audit\_p0_full_integration.log (179 tests, 69.36s)
- D:\AIOS\_agent-hub\audit\2026-10-10-P0-kernel-ci-baseline.md (this)

--- Codex supervisor - P0 kernel CI baseline DONE - 22/22 critical + 179/179 full integration - 2026-10-10
