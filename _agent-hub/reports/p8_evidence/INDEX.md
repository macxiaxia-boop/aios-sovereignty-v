# AIOS Core Spine P8 Evidence Index · v2026-10-09 (real pytest -v output embedded)

**Date**: 2026-10-09T02:40:35.439960+00:00
**Tests run**: 24 collected (24 parsed)
**Status**: 24/24 PASSED

## Per-test PASS.md files (each contains real pytest -v head + tail)

| Test | Status | Position | File |
|---|---|---|---|
| `test_t07_hermes_subprocess_timeout` | PASSED | 4% | `p8_T07_t07_hermes_subprocess_timeout_PASS.md` |
| `test_t08_hermes_invalid_subcommand_falls_back_to_doctor` | PASSED | 8% | `p8_T08_t08_hermes_invalid_subcommand_falls_back_to_doctor_PASS.md` |
| `test_t09_openclaw_connection_refused` | PASSED | 12% | `p8_T09_t09_openclaw_connection_refused_PASS.md` |
| `test_t10_openclaw_unknown_action_routes_to_health` | PASSED | 16% | `p8_T10_t10_openclaw_unknown_action_routes_to_health_PASS.md` |
| `test_t11_workbuddy_probe_returns_honest_evidence` | PASSED | 20% | `p8_T11_t11_workbuddy_probe_returns_honest_evidence_PASS.md` |
| `test_t12_workbuddy_dispatch_blocked_with_evidence` | PASSED | 25% | `p8_T12_t12_workbuddy_dispatch_blocked_with_evidence_PASS.md` |
| `test_t13_parallel_dispatch_all_adapters` | PASSED | 29% | `p8_T13_t13_parallel_dispatch_all_adapters_PASS.md` |
| `test_t14_hermes_large_output_truncation` | PASSED | 33% | `p8_T14_t14_hermes_large_output_truncation_PASS.md` |
| `test_t15_set_dispatcher_injects_each_adapter` | PASSED | 37% | `p8_T15_t15_set_dispatcher_injects_each_adapter_PASS.md` |
| `test_t16_hermes_burst_10_envelopes` | PASSED | 41% | `p8_T16_t16_hermes_burst_10_envelopes_PASS.md` |
| `test_t17_openclaw_burst_10_envelopes` | PASSED | 45% | `p8_T17_t17_openclaw_burst_10_envelopes_PASS.md` |
| `test_t18_idempotent_retry_of_same_envelope` | PASSED | 50% | `p8_T18_t18_idempotent_retry_of_same_envelope_PASS.md` |
| `test_t19_goalguard_allows_normal_hermes_task` | PASSED | 54% | `p8_T19_t19_goalguard_allows_normal_hermes_task_PASS.md` |
| `test_t20_real_hermes_dispatch_end_to_end` | PASSED | 58% | `p8_T20_t20_real_hermes_dispatch_end_to_end_PASS.md` |
| `test_t21_real_openclaw_dispatch_end_to_end` | PASSED | 62% | `p8_T21_t21_real_openclaw_dispatch_end_to_end_PASS.md` |
| `test_t22_real_workbuddy_probe_end_to_end` | PASSED | 66% | `p8_T22_t22_real_workbuddy_probe_end_to_end_PASS.md` |
| `test_t23_resume_after_partial_failure` | PASSED | 70% | `p8_T23_t23_resume_after_partial_failure_PASS.md` |
| `test_t24_e2e_three_adapters_full_smoke` | PASSED | 75% | `p8_T24_t24_e2e_three_adapters_full_smoke_PASS.md` |
| `test_verifier_hermes_subprocess` | PASSED | 79% | `p8_VERIFIER_verifier_hermes_subprocess_PASS.md` |
| `test_verifier_openclaw_http` | PASSED | 83% | `p8_VERIFIER_verifier_openclaw_http_PASS.md` |
| `test_verifier_workbuddy_probe` | PASSED | 87% | `p8_VERIFIER_verifier_workbuddy_probe_PASS.md` |
| `test_verifier_all_three_adapters_combined` | PASSED | 91% | `p8_VERIFIER_verifier_all_three_adapters_combined_PASS.md` |
| `test_subprocess_retry_uses_exponential_backoff` | PASSED | 95% | `p8_DISPATCH_RUNTIME_subprocess_retry_uses_exponential_backoff_PASS.md` |
| `test_subprocess_parallelism_is_capped_at_three` | PASSED | 100% | `p8_DISPATCH_RUNTIME_subprocess_parallelism_is_capped_at_three_PASS.md` |

## Re-run command

```bash
cd D:\AIOS\_agent-hub\v2
python -m pytest tests/test_p8_t*.py tests/test_verifier.py tests/test_dispatch_runtime.py -v --tb=short -p no:anyio
```

Result: **24 passed in 47.64s** (latest run, after fixing asyncio plugin issue with `-p no:anyio`)

Full output: `D:\AIOS\_agent-hub\reports\p8_full_pytest_output_v2.txt` (2507 bytes)
