# Strategy alias correction — Evidence (2026-10-09)

**Contract**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_ALIAS_CORRECTION_20261009.md`
**Policy**: `GLOBAL_PRODUCT_STRATEGY` / version `2026-10-08`
**Executor**: Claude Code 2.1.285 (MiniMax-M3)
**Date (UTC)**: 2026-10-09

---

## 1. Scope

Independent verification found that the Phase-2 policy / gate / scanner blocked
synthetic IDs like `industry-zhuangxiu` but missed real Chinese aliases
that appear in the quarantined WorkBuddy memory file (医美, 装企, 行业垂直,
灵策智算, 灵策AI, and old CloudTech/V22/V23 wording, old skill IDs
`sk-industry` / `sk-cross-matrix`, and vertical-workflow terms).

The smallest evidence-backed correction:
1. Add `retired_aliases` + `retired_alias_kind` to the policy.
2. Update StrategyGate to combine alias hits with structured-field presence
   and other signals (retired ids / assets / source context).
3. Update ContaminationScanner to include aliases in the content-token set
   (preserving binary / secret / size guards).
4. Add tests against the real quarantined memory file, synthetic active
   files / task envelopes, and false-positive generics.
5. Refresh the SHA-256 sidecar.

## 2. Files touched

| Path | Kind | Bytes / Lines |
|---|---|---|
| `policy/product_strategy.v1.json` | modified | +`retired_aliases` (19) +`retired_alias_kind` (5 buckets) |
| `policy/product_strategy.v1.schema.json` | modified | added `retired_aliases` and `retired_alias_kind` to required + properties |
| `policy/product_strategy.v1.sha256` | modified | refreshed hash |
| `policy/strategy_index.json` | modified | bumped `index_version` → `2026-10-09`, added `alias_correction` block |
| `policy/strategy_policy.py` | modified | `REQUIRED_FIELDS` + new validator + helpers `is_retired_alias`, `retired_alias_kind_of` |
| `policy/strategy_gate.py` | modified | alias-scan branch with combined-source-context rule + new helper `_alias_in_structured_fields` |
| `policy/contamination_scanner.py` | modified | `build_content_token_set` now includes `retired_aliases` |
| `v2/tests/test_strategy_alias_correction.py` | **NEW** | 23 tests |
| `reports/GLOBAL_STRATEGY_ALIAS_CORRECTION_20261009_EVIDENCE.json` | **NEW** | structured evidence |
| `reports/GLOBAL_STRATEGY_ALIAS_CORRECTION_20261009_EVIDENCE.md` | **NEW** | this file |

## 3. Policy invariants (SSOT audit)

| Field | Value |
|---|---|
| `policy_id` | `GLOBAL_PRODUCT_STRATEGY` |
| `policy_version` | `2026-10-08` |
| `policy.json` SHA-256 | `270B9A02C76D0F9F904E3E1F9693CDE167C63D96B02B45DA3B8D29D7971FED74` |
| `policy.schema.json` SHA-256 | (verified; recorded in evidence JSON) |
| `sidecar` SHA-256 | matches the JSON file (fail-closed otherwise) |
| Loader result | `ok=True, reason=""` |
| `retired_aliases` count | **19** |
| `retired_alias_kind` buckets | `industry_vertical` (6) · `old_brand` (3) · `vertical_workflow` (3) · `cloudtech_v22_v23` (5) · `skill_id` (2) |

### Retired aliases (full list)

```
医美                              kind=industry_vertical
装企                              kind=industry_vertical
家居/医美                         kind=industry_vertical
行业垂直                          kind=industry_vertical
行业垂直文档                      kind=industry_vertical
行业MVP                           kind=industry_vertical
灵策智算                          kind=old_brand
灵策AI                            kind=old_brand
Phase 1 行业 SaaS                 kind=old_brand
装修矩阵                          kind=vertical_workflow
装修矩阵V2                        kind=vertical_workflow
小红书仿写管线                    kind=vertical_workflow
CloudTech V22                     kind=cloudtech_v22_v23
CloudTech V23                     kind=cloudtech_v22_v23
CloudTechV22Monitor               kind=cloudtech_v22_v23
CloudTech_V22Watchdog             kind=cloudtech_v22_v23
CloudTech_V23FileWatcher          kind=cloudtech_v22_v23
sk-industry                       kind=skill_id
sk-cross-matrix                   kind=skill_id
```

Generic words explicitly excluded: `industry`, `marketing`, `AI`, `SaaS`,
`marketing automation`. None appear in `retired_aliases`.

## 4. Real quarantined memory file scan

`D:\AIOS\_quarantine\retired-assets\20261008\memory\45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md`

- SHA-256: `B8415F112F7695CDD3803716CDA38A0FF68FD4804C4B8C9BFCD5C79EBF6BB594`
- Size: 5,514 bytes (matches `quarantine_manifest.json`)
- Scanned findings (content-level): 8+ aliases
  - `医美`, `装企`, `家居/医美`, `行业垂直`, `行业垂直文档`,
    `灵策智算`, `灵策AI`, `Phase 1 行业 SaaS`
- Classification: ALL `ARCHIVED_REFERENCE` (source = `quarantine`)
- Zero `ACTIVE_VIOLATION` findings (proves quarantine is not double-billed).

## 5. Synthetic ACTIVE-loadable file scan

A file at a fresh `active_loader/` path containing
`switch the AI context to 医美+装企 MVP through 灵策智算`:

| matched_token | classification | source |
|---|---|---|
| 医美 | ACTIVE_VIOLATION | active |
| 装企 | ACTIVE_VIOLATION | active |
| 灵策智算 | ACTIVE_VIOLATION | active |

(Active loadable file content alias hit → ACTIVE_VIOLATION, the gate
catches active re-introduction.)

## 6. StrategyGate scenarios (10 scenarios, all expected match actual)

| # | Scenario | Expected | Actual | Blocking event(s) |
|---|---|---|---|---|
| 1 | `医美 + 装企` in title | BLOCK | BLOCK | STRATEGY_DRIFT_DETECTED |
| 2 | `装企` in description | BLOCK | BLOCK | STRATEGY_DRIFT_DETECTED |
| 3 | `CloudTech V22` in title | BLOCK | BLOCK | DEPRECATED_ASSET_REFERENCED |
| 4 | `sk-industry` + `sk-cross-matrix` in text | BLOCK | BLOCK | DEPRECATED_ASSET_REFERENCED |
| 5 | `industry` (bare EN) | ALLOW | ALLOW | – |
| 6 | bare `行业` (no compound) | ALLOW | ALLOW | – |
| 7 | `AI` (bare EN) | ALLOW | ALLOW | – |
| 8 | `SaaS` (bare EN) | ALLOW | ALLOW | – |
| 9 | `医美` only in `note` (no structured field) | ALLOW (WARN) | ALLOW | – |
| 10 | Valid horizontal marketing | ALLOW | ALLOW | – |

## 7. Test results (111 / 111 PASSED)

```
tests/test_strategy_policy.py ..........                                 [  9%]
tests/test_requirements_lifecycle.py ..........                          [ 18%]
tests/test_contamination_scanner.py .............................        [ 44%]
tests/test_quarantine_allowlist.py .......                               [ 50%]
tests/test_strategy_gate.py ..........                                   [ 59%]
tests/test_strategy_hook_integration.py ........                         [ 66%]
tests/test_strategy_gate_submit_task.py ..............                   [ 79%]
tests/test_strategy_alias_correction.py .......................          [100%]
============================= 111 passed in 0.71s =============================
```

## 8. Fail-closed invariants (loader / schema)

| Scenario | Reason | Loader result |
|---|---|---|
| `retired_aliases` removed | `schema_violation` | `ok=False` |
| `retired_alias_kind` references alias not in `retired_aliases` | `schema_violation` | `ok=False` |
| `retired_aliases` contains empty string | `schema_violation` | `ok=False` |
| `retired_aliases` contains single-character entry | `schema_violation` | `ok=False` |
| SHA-256 sidecar mismatch | `hash_mismatch` | `ok=False` |
| Wrong owner | `policy_identity_mismatch` | `ok=False` |
| Missing JSON file | `missing_policy_file` | `ok=False` |
| Malformed JSON | `malformed_json` | `ok=False` |

## 9. Red lines observed (no touches)

| Surface | Result |
|---|---|
| `_agent-hub/AGENTS.md` | UNTOUCHED |
| `kernel/src/aios_kernel/domain/goal.py` | UNTOUCHED |
| `kernel/src/aios_kernel/domain/decision.py` | UNTOUCHED |
| `kernel/src/aios_kernel/verifier/deterministic.py` | UNTOUCHED |
| `_agent-hub/policy/model-policy.v1.yaml` | UNTOUCHED |
| `_agent-hub/v2/src/v2_consumer.py` | **0 lines diff** (verified by `test_v2_consumer_diff_is_zero_lines`) |
| CloudTech V22 gateway at `127.0.0.1:5099` | LIVE (not stopped) |
| 7 CloudTech scheduled tasks | UNTOUCHED |
| `D:\AIOS\cloudtech-saas\` / `D:\CloudTech-*` | UNTOUCHED |
| `E:\AI_Backup` | UNTOUCHED |
| Git history | NOT REWRITTEN |

## 10. Out-of-scope (deferred; not modified)

- Live CloudTech gateway teardown
- `CloudTechV22Monitor` service stop/delete
- 5 CloudTech scheduled task deletes
- `E:\AI_Backup` mirror scope change
- Root installer scripts (`install_aios_loop.cmd`, etc.)
- Out-of-scope `D:\CloudTech-*` directories
- Archive directory deletes
- `daemons_v2` services uninstall
- R65 residual tasks
- Daily backup task
- Git history rewrite
- HKCU Run keys
- Codex session archive
- Cloud backup purge

All remain `requires_authorization` per AGENTS.md.

## 11. Bounded correction summary

- **Single SSOT edit**: `product_strategy.v1.json` (+ `retired_aliases` + `retired_alias_kind`).
- **Schema aligned**: `product_strategy.v1.schema.json` lists both as required.
- **Loader hardened**: `strategy_policy.py` validates uniqueness, length, and
  kind-bucket consistency (no orphan aliases in `retired_alias_kind`).
- **Gate wired**: `strategy_gate.py` scans structured fields + text, combines
  alias hit with structured-field presence OR combined signal
  OR `cloudtech_v22_v23` / `skill_id` kind → BLOCK.
- **Scanner wired**: `contamination_scanner.build_content_token_set` now
  includes aliases (≥2 chars; refuses bare single-character noise).
- **Tests**: 23 new + 88 pre-existing strategy tests = 111/111 PASSED.
- **Evidence**: this file + JSON sibling.

**No service touched. No history rewritten. No personal file deleted. No
product code modified.**
