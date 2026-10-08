# P8 22/22 PASS Evidence Index (2026-10-08 Summit)

- **Captured at (UTC)**: 2026-10-08T15:48:50Z
- **Captured at (Beijing)**: 2026-10-08T23:48:50+08:00
- **Run summary**: `22 passed, 22 warnings in 53.58s`
- **Tests**: 22 PASSED, 0 FAILED, 0 ERROR

| # | Test ID | Slug | Pytest function | Source file | Evidence file |
| - | ------- | ---- | --------------- | ----------- | ------------- |
| 1 | T07 | hermes_subprocess_timeout | `test_t07_hermes_subprocess_timeout` | `test_p8_t07.py` | [p8_T07_hermes_subprocess_timeout_PASS.md](./p8_T07_hermes_subprocess_timeout_PASS.md) |
| 2 | T08 | hermes_invalid_subcommand_to_doctor | `test_t08_hermes_invalid_subcommand_falls_back_to_doctor` | `test_p8_t08.py` | [p8_T08_hermes_invalid_subcommand_to_doctor_PASS.md](./p8_T08_hermes_invalid_subcommand_to_doctor_PASS.md) |
| 3 | T09 | openclaw_connection_refused | `test_t09_openclaw_connection_refused` | `test_p8_t09.py` | [p8_T09_openclaw_connection_refused_PASS.md](./p8_T09_openclaw_connection_refused_PASS.md) |
| 4 | T10 | openclaw_unknown_action_to_health | `test_t10_openclaw_unknown_action_routes_to_health` | `test_p8_t10.py` | [p8_T10_openclaw_unknown_action_to_health_PASS.md](./p8_T10_openclaw_unknown_action_to_health_PASS.md) |
| 5 | T11 | workbuddy_probe_honest | `test_t11_workbuddy_probe_returns_honest_evidence` | `test_p8_t11.py` | [p8_T11_workbuddy_probe_honest_PASS.md](./p8_T11_workbuddy_probe_honest_PASS.md) |
| 6 | T12 | workbuddy_dispatch_blocked | `test_t12_workbuddy_dispatch_blocked_with_evidence` | `test_p8_t12.py` | [p8_T12_workbuddy_dispatch_blocked_PASS.md](./p8_T12_workbuddy_dispatch_blocked_PASS.md) |
| 7 | T13 | parallel_dispatch_all_adapters | `test_t13_parallel_dispatch_all_adapters` | `test_p8_t13.py` | [p8_T13_parallel_dispatch_all_adapters_PASS.md](./p8_T13_parallel_dispatch_all_adapters_PASS.md) |
| 8 | T14 | hermes_large_output_truncation | `test_t14_hermes_large_output_truncation` | `test_p8_t14.py` | [p8_T14_hermes_large_output_truncation_PASS.md](./p8_T14_hermes_large_output_truncation_PASS.md) |
| 9 | T15 | set_dispatcher_di | `test_t15_set_dispatcher_injects_each_adapter` | `test_p8_t15.py` | [p8_T15_set_dispatcher_di_PASS.md](./p8_T15_set_dispatcher_di_PASS.md) |
| 10 | T16 | hermes_burst_10_envelopes | `test_t16_hermes_burst_10_envelopes` | `test_p8_t16.py` | [p8_T16_hermes_burst_10_envelopes_PASS.md](./p8_T16_hermes_burst_10_envelopes_PASS.md) |
| 11 | T17 | openclaw_burst_10_envelopes | `test_t17_openclaw_burst_10_envelopes` | `test_p8_t17.py` | [p8_T17_openclaw_burst_10_envelopes_PASS.md](./p8_T17_openclaw_burst_10_envelopes_PASS.md) |
| 12 | T18 | idempotent_retry_envelope | `test_t18_idempotent_retry_of_same_envelope` | `test_p8_t18.py` | [p8_T18_idempotent_retry_envelope_PASS.md](./p8_T18_idempotent_retry_envelope_PASS.md) |
| 13 | T19 | goalguard_allows_normal_hermes | `test_t19_goalguard_allows_normal_hermes_task` | `test_p8_t19.py` | [p8_T19_goalguard_allows_normal_hermes_PASS.md](./p8_T19_goalguard_allows_normal_hermes_PASS.md) |
| 14 | T20 | real_hermes_dispatch_e2e | `test_t20_real_hermes_dispatch_end_to_end` | `test_p8_t20.py` | [p8_T20_real_hermes_dispatch_e2e_PASS.md](./p8_T20_real_hermes_dispatch_e2e_PASS.md) |
| 15 | T21 | real_openclaw_dispatch_e2e | `test_t21_real_openclaw_dispatch_end_to_end` | `test_p8_t21.py` | [p8_T21_real_openclaw_dispatch_e2e_PASS.md](./p8_T21_real_openclaw_dispatch_e2e_PASS.md) |
| 16 | T22 | real_workbuddy_probe_e2e | `test_t22_real_workbuddy_probe_end_to_end` | `test_p8_t22.py` | [p8_T22_real_workbuddy_probe_e2e_PASS.md](./p8_T22_real_workbuddy_probe_e2e_PASS.md) |
| 17 | T23 | resume_after_partial_failure | `test_t23_resume_after_partial_failure` | `test_p8_t23.py` | [p8_T23_resume_after_partial_failure_PASS.md](./p8_T23_resume_after_partial_failure_PASS.md) |
| 18 | T24 | e2e_three_adapters_full_smoke | `test_t24_e2e_three_adapters_full_smoke` | `test_p8_t24.py` | [p8_T24_e2e_three_adapters_full_smoke_PASS.md](./p8_T24_e2e_three_adapters_full_smoke_PASS.md) |
| 19 | VERIFIER_HERMES | verifier_hermes_subprocess | `test_verifier_hermes_subprocess` | `test_verifier.py` | [p8_VERIFIER_HERMES_verifier_hermes_subprocess_PASS.md](./p8_VERIFIER_HERMES_verifier_hermes_subprocess_PASS.md) |
| 20 | VERIFIER_OPENCLAW | verifier_openclaw_http | `test_verifier_openclaw_http` | `test_verifier.py` | [p8_VERIFIER_OPENCLAW_verifier_openclaw_http_PASS.md](./p8_VERIFIER_OPENCLAW_verifier_openclaw_http_PASS.md) |
| 21 | VERIFIER_WORKBUDDY | verifier_workbuddy_probe | `test_verifier_workbuddy_probe` | `test_verifier.py` | [p8_VERIFIER_WORKBUDDY_verifier_workbuddy_probe_PASS.md](./p8_VERIFIER_WORKBUDDY_verifier_workbuddy_probe_PASS.md) |
| 22 | VERIFIER_COMBINED | verifier_all_three_combined | `test_verifier_all_three_adapters_combined` | `test_verifier.py` | [p8_VERIFIER_COMBINED_verifier_all_three_combined_PASS.md](./p8_VERIFIER_COMBINED_verifier_all_three_combined_PASS.md) |
