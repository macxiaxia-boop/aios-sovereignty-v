# P8 Evidence Audit — 2026-10-09

- **Auditor:** Codex worker
- **Captured:** 2026-10-09T09:58:00+08:00
- **Scope:** `D:\AIOS\_agent-hub\reports\p8_evidence\INDEX.md` and all 22 `*_PASS.md` evidence files.
- **Required PASS.md contract:** test name + embedded `pytest -v` output head and tail + timestamp + `status=PASS`.

## Verdict

- Evidence files found: **22**; INDEX claims 22/22.
- Shared output file exists: **True** (`D:\AIOS\_agent-hub\reports\p8_full_pytest_output.txt`).
- Every PASS.md contains a test function, UTC timestamp, and a `Status: PASS` field.
- **None of the 22 PASS.md files embeds the required pytest output head and tail.** They contain one representative test line and a pointer to the shared output file. Therefore all 22 are **BLOCKED** for the user’s stricter evidence contract; the shared file is a separate artifact and cannot substitute for the required per-file output.
- The shared output file is not labeled with a `pytest -v` command line and is not repeated per evidence file; this is recorded as an evidence provenance gap, not as a hidden PASS.

## Per-file audit

| # | Evidence file | Pytest function | Timestamp | Status field | Embedded output head+tail | Audit status |
|---:|---|---|---|---|---|---|
| 1 | `p8_T07_hermes_subprocess_timeout_PASS.md` | `test_t07_hermes_subprocess_timeout` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 2 | `p8_T08_hermes_invalid_subcommand_to_doctor_PASS.md` | `test_t08_hermes_invalid_subcommand_falls_back_to_doctor` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 3 | `p8_T09_openclaw_connection_refused_PASS.md` | `test_t09_openclaw_connection_refused` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 4 | `p8_T10_openclaw_unknown_action_to_health_PASS.md` | `test_t10_openclaw_unknown_action_routes_to_health` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 5 | `p8_T11_workbuddy_probe_honest_PASS.md` | `test_t11_workbuddy_probe_returns_honest_evidence` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 6 | `p8_T12_workbuddy_dispatch_blocked_PASS.md` | `test_t12_workbuddy_dispatch_blocked_with_evidence` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 7 | `p8_T13_parallel_dispatch_all_adapters_PASS.md` | `test_t13_parallel_dispatch_all_adapters` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 8 | `p8_T14_hermes_large_output_truncation_PASS.md` | `test_t14_hermes_large_output_truncation` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 9 | `p8_T15_set_dispatcher_di_PASS.md` | `test_t15_set_dispatcher_injects_each_adapter` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 10 | `p8_T16_hermes_burst_10_envelopes_PASS.md` | `test_t16_hermes_burst_10_envelopes` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 11 | `p8_T17_openclaw_burst_10_envelopes_PASS.md` | `test_t17_openclaw_burst_10_envelopes` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 12 | `p8_T18_idempotent_retry_envelope_PASS.md` | `test_t18_idempotent_retry_of_same_envelope` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 13 | `p8_T19_goalguard_allows_normal_hermes_PASS.md` | `test_t19_goalguard_allows_normal_hermes_task` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 14 | `p8_T20_real_hermes_dispatch_e2e_PASS.md` | `test_t20_real_hermes_dispatch_end_to_end` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 15 | `p8_T21_real_openclaw_dispatch_e2e_PASS.md` | `test_t21_real_openclaw_dispatch_end_to_end` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 16 | `p8_T22_real_workbuddy_probe_e2e_PASS.md` | `test_t22_real_workbuddy_probe_end_to_end` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 17 | `p8_T23_resume_after_partial_failure_PASS.md` | `test_t23_resume_after_partial_failure` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 18 | `p8_T24_e2e_three_adapters_full_smoke_PASS.md` | `test_t24_e2e_three_adapters_full_smoke` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 19 | `p8_VERIFIER_COMBINED_verifier_all_three_combined_PASS.md` | `test_verifier_all_three_adapters_combined` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 20 | `p8_VERIFIER_HERMES_verifier_hermes_subprocess_PASS.md` | `test_verifier_hermes_subprocess` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 21 | `p8_VERIFIER_OPENCLAW_verifier_openclaw_http_PASS.md` | `test_verifier_openclaw_http` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |
| 22 | `p8_VERIFIER_WORKBUDDY_verifier_workbuddy_probe_PASS.md` | `test_verifier_workbuddy_probe` | `2026-10-08T15:48:50Z` | `PASS` | NO | **BLOCKED** |

## Blocking reason

`BLOCKED — missing embedded pytest -v output head and tail in this PASS.md; only a reference to `D:\AIOS\_agent-hub\reports\p8_full_pytest_output.txt` is present.`

## Scope boundary

This audit did not rewrite evidence files or manufacture a fresh P8 run. The existing shared run reports `22 passed, 22 warnings in 53.58s`, but that historical aggregate cannot satisfy the requested per-file head/tail proof.
