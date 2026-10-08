# P8 Full Acceptance — 18/18 PASS

**Date**: 2026-10-08  
**Suite**: tests/test_p8_t07.py → tests/test_p8_t24.py  
**Result**: **18 passed, 18 warnings in 48.30s**  
**Status**: ✅ ALL GREEN

## Coverage matrix

| Test ID | Category | Adapter | Real call | Result |
|---------|----------|---------|-----------|--------|
| T07 | fault injection | hermes | subprocess timeout (1s cap) | PASS |
| T08 | fault injection | hermes | invalid subcommand → doctor fallback | PASS |
| T09 | fault injection | openclaw | connection refused (wrong port) | PASS |
| T10 | fault injection | openclaw | unknown action → /healthz fallback | PASS |
| T11 | fault injection | workbuddy | probe with daemon stale 16200s | PASS |
| T12 | fault injection | workbuddy | dispatch blocked with evidence | PASS |
| T13 | parallel | all 3 | concurrent dispatch | PASS |
| T14 | large output | hermes | sessions list → stdout truncation | PASS |
| T15 | DI | all 3 | set_dispatcher injects each adapter | PASS |
| T16 | burst | hermes | 10 sequential dispatches | PASS |
| T17 | burst | openclaw | 10 HTTP GET dispatches | PASS |
| T18 | idempotency | openclaw | same envelope dispatched twice | PASS |
| T19 | GoalGuard | hermes | normal task passes guard | PASS |
| T20 | real live | hermes | real subprocess → ack + result | PASS |
| T21 | real live | openclaw | real /healthz → ack + result | PASS |
| T22 | real live | workbuddy | real probe → ack + result | PASS |
| T23 | resume | hermes | failing dispatcher + working resume | PASS |
| T24 | e2e smoke | all 3 | full lifecycle for each adapter | PASS |

## Adapters delivered

| Adapter | File | Lines | Real transport | Status |
|---------|------|-------|----------------|--------|
| hermes | `v2/src/hermes_adapter.py` | 174 | hermes.exe subprocess | ✅ LIVE |
| openclaw | `v2/src/openclaw_adapter.py` | 178 | urllib HTTP to 127.0.0.1:18792 | ✅ LIVE |
| workbuddy | `v2/src/workbuddy_adapter.py` | 169 | file/process probe (daemon DOWN) | ⚠ HONEST BLOCKED |

## Verifier

- `v2/src/verifier.py` (298 lines) — independent verification that re-runs hermes.exe, re-issues /healthz, re-reads daemon.log
- All 3 recipients verify_ok=true (substrings match, body matches, staleness matches)

## Raw pytest output

See `D:\AIOS\_agent-hub\reports\p8_full_pytest_output.txt`
