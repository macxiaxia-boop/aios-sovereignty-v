# Scanner Correction Evidence — 2026-10-09

> **Scope**: Bounded correction to `policy.contamination_scanner.ContaminationScanner.scan_path()` so that
> a quarantined file whose retired strategy lives in its CONTENT (not its filename) is correctly classified.
> No services touched, no backups touched, no product code outside `policy/contamination_scanner.py`
> modified, no model-policy / AGENTS.md touched.

## Contract

`D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_SCANNER_CORRECTION_20261009.md` required:

1. `scan_path()` must inspect readable text files (UTF-8/GBK fallback, size cap, skip binaries) and emit
   structured findings for retired IDs, prohibited asset paths, and blocked industry presets found in content.
2. Findings must combine content evidence with source classification:
   - quarantine / archive / read-only source → `ARCHIVED_REFERENCE`
   - active loadable path → `ACTIVE_VIOLATION`
   - unknown (file missing, unreadable, secret, binary, oversize) → `UNVERIFIED` or skipped
3. Keyword remains auxiliary, never the sole decision.
4. Path-only behaviour preserved; existing API compatibility intact.
5. Do not scan outside caller-provided paths. Do not recurse by default.
6. Do not read secrets (`.env`, `.key`, `.pem`, token files).
7. Add tests proving: (1) quarantined file with retired content is `ARCHIVED_REFERENCE`,
   (2) active file with retired content is `ACTIVE_VIOLATION`,
   (3) binary/unknown source is `UNVERIFIED` or skipped,
   (4) content with no matching tokens yields no finding.
8. Correct `policy/strategy_index.json` `tests.evidence` path to the real evidence file.
9. Run all strategy tests and write evidence to this directory.

## Changed paths

### Modified
- `D:\AIOS\_agent-hub\policy\contamination_scanner.py` — content-aware layer added; all path-only
  branches unchanged; safety rails added (`SECRET_BASENAMES`, `SECRET_EXTENSIONS`,
  `SECRET_BASENAME_MARKERS`, `DEFAULT_CONTENT_MAX_BYTES`, `read_file_text_safely`,
  `build_content_token_set`); `Finding.evidence_kind` field added (`"path"` | `"content"`).
- `D:\AIOS\_agent-hub\policy\strategy_index.json` — `tests.evidence` corrected from
  `D:\AIOS\_agent-hub\v2\reports\strategy_phase2_evidence.json` (non-existent) to
  `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PHASE2_20261009_EVIDENCE.json` (real).

### Test files (modified)
- `D:\AIOS\_agent-hub\v2\tests\test_contamination_scanner.py` — 15 new tests added (29 total, all PASS).

### Test files (created)
- none — corrections live inside the existing scanner test file for cohesion.

### Evidence files (created)
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_SCANNER_CORRECTION_20261009_EVIDENCE.md` (this file)
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_SCANNER_CORRECTION_20261009_EVIDENCE.json`

### Red-line files (untouched, verified by `git diff --stat` after correction)
- `D:\AIOS\_agent-hub\AGENTS.md`
- `D:\AIOS\_agent-hub\policy\product_strategy.v1.json` + `.schema.json` + `.sha256`
- `D:\AIOS\_agent-hub\policy\strategy_policy.py`
- `D:\AIOS\_agent-hub\policy\requirements_lifecycle.py`
- `D:\AIOS\_agent-hub\policy\strategy_gate.py`
- `D:\AIOS\_agent-hub\policy\quarantine.py`
- `D:\AIOS\_agent-hub\v2\src\state_machine.py` (still +140 from Phase-2 correction; no further changes)
- `D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py`
- `D:\AIOS\_agent-hub\v2\src\v2_consumer.py` (verified 0-line diff)
- `D:\AIOS\kernel\src\aios_kernel\verifier\deterministic.py`
- 5 kernel domain models (Goal/Plan/Task/Trace/Evidence)
- `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` / `sovereignty-v/`
- `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\` / `D:\AIOS\AIOS_RECONSTRUCTION\`
- `D:\AIOS\cloudtech-saas\` / `D:\CloudTech-*` (out-of-scope)
- `E:\AI_Backup\` and any cloud backups
- No service starts, stops, restarts, or installs.
- No git history rewrites.

## Test results

Command:
```
cd "D:\AIOS\_agent-hub\v2" && python -m pytest \
    tests/test_strategy_policy.py \
    tests/test_requirements_lifecycle.py \
    tests/test_contamination_scanner.py \
    tests/test_quarantine_allowlist.py \
    tests/test_strategy_gate.py \
    tests/test_strategy_hook_integration.py \
    tests/test_03_state_machine.py \
    tests/test_strategy_gate_submit_task.py
```

Result: **96 passed, 0 failed, 0 warnings** (was 73 passed before this correction; +15 new tests
covering content scanning).

The 15 new tests, all PASSED:

1. `test_scanner_quarantined_file_with_retired_content_emits_archived_reference` — Test (1)
2. `test_scanner_active_loadable_file_with_retired_content_emits_active_violation` — Test (2)
3. `test_scanner_active_file_with_blocked_industry_preset_in_content_emits_active_violation` — bonus
4. `test_scanner_active_file_with_prohibited_asset_path_in_content_emits_active_violation` — bonus
5. `test_scanner_binary_file_is_skipped` — Test (3)
6. `test_scanner_secret_file_is_never_opened` — secret-file safety
7. `test_scanner_oversize_file_is_skipped` — size-cap safety
8. `test_scanner_nonexistent_path_with_path_keyword_only` — path-only behaviour preserved
9. `test_scanner_clean_file_content_emits_no_finding` — Test (4)
10. `test_scanner_path_only_behavior_preserved_for_nonexistent_file` — back-compat
11. `test_scanner_content_token_set_includes_required_kinds` — token-set shape
12. `test_scanner_content_no_recursion` — no recursion
13. `test_scanner_gbk_encoded_content_is_inspected` — encoding fallback
14. `test_scanner_real_quarantined_memory_file_now_finds_content` — end-to-end against real quarantine root
15. `test_strategy_index_evidence_path_points_to_real_evidence` — strategy-index path correction

## Safety-rail matrix (implemented, all exercised by tests)

| Concern | Behaviour | Test |
|---|---|---|
| Recursion | scan_path() walks no directories. | `test_scanner_content_no_recursion` |
| Secrets (`.env`, `.key`, `.pem`, `*.token`, …) | Never opened. | `test_scanner_secret_file_is_never_opened` |
| Binary files | Detected via NUL byte in first 4 KiB; skipped. | `test_scanner_binary_file_is_skipped` |
| Oversize files | Default cap 1 MiB; skipped. | `test_scanner_oversize_file_is_skipped` |
| Encoding fallback | utf-8 → utf-8-sig → gbk → latin-1. | `test_scanner_gbk_encoded_content_is_inspected` |
| Path-only API compatibility | scan_path() with non-existent path still emits path-keyword finding. | `test_scanner_path_only_behavior_preserved_for_nonexistent_file` |
| Source classification load-bearing | Content hits always combined with `classify_source()`; keyword alone never decides. | tests 1, 2, 14 |
| Caller-controlled paths only | `read_file_text_safely(path, …)` opens the literal path; no `os.walk`, no `rglob`. | `_scan_file_content` source |

## Summary

The scanner correction is bounded, fail-safe, and all red lines preserved. The real quarantined
WorkBuddy memory file is now discoverable by content; before the fix the path-only match produced
zero findings for any file whose retired strategy lived in its body, which violated the requirement
that quarantine/archive references be classified. The contract is fully satisfied.