# T1 yaml recover - 2026-10-10

## Status: DONE (yaml parse OK, EX-001~010 IDENTICAL, sha synced)

## Before
- size: 7701 B
- sha: 50A515C2B23B318FE832BD35CA47185D101A4076DF2DDADACA0ECC2852ECE68F
- manifest sha: E8A9DEA3E0... (mismatched, regex test would have used yaml.safe_load which fails)
- yaml.safe_load FAIL at line 48 (expected <block end>, but found '-')
- EX-001 block at 4-space indent, no `exception_rules:` parent declared

## Fix (additive only)
1. Inserted `  exception_rules:` (2-space indent) right after `audit_log:` line and a blank line
2. Re-parsed: yaml.safe_load OK, 10 EX rules detected
3. Appended EX-011 block before `adapter:` section
4. Re-parsed: yaml.safe_load OK, 11 EX rules

## After
- size: 8271 B
- sha: 89CA730593FF150F7B409E285FBF27FD844610CFD9D724522027AAEEBC052D6C
- yaml.safe_load: PARSE OK
- exception_rules count: 11 (EX-001~011)
- 4 adapter reconcile will use yaml.safe_load directly

## Red-line byte verification (WT vs HEAD)
```
EX-001: IDENTICAL
EX-002: IDENTICAL
EX-003: IDENTICAL
EX-004: IDENTICAL
EX-005: IDENTICAL
EX-006: IDENTICAL
EX-007: IDENTICAL
EX-008: IDENTICAL
EX-009: IDENTICAL
EX-010: IDENTICAL
RED-LINE OK
```

## Manifest sha sync
- sha256: 89CA730593FF150F7B409E285FBF27FD844610CFD9D724522027AAEEBC052D6C (matches yaml)
- size_bytes: 8271
- + 3 footer lines (updated_at, updated_reason, verification_status)
- All existing lines preserved

## Side effect
- adapters_registry.py was MISSING from earlier session (reverted). Will be re-created in T2.
- yaml.safe_load now works correctly. Existing W8 adapter runtimes can be re-tuned to use it.

## Files
- model-policy.v1.yaml        8271 B  sha256=89CA730593FF150F7B409E285FBF27FD844610CFD9D724522027AAEEBC052D6C
- model-policy.v1.sha256       updated  manifest sha matches yaml sha
- _recovery_t1.py              helper script (created)

--- Codex supervisor - T1 yaml recover DONE - parse OK + EX-001~010 IDENTICAL - 2026-10-10
