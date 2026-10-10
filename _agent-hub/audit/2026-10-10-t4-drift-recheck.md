# T4 drift real recheck - 2026-10-10 (P0 fix 后)

## Status: DONE - drift=145 (down from 172)

## Method
- Used reconciler.scan_profile_files() + check_compliance() with FRESH yaml (post-T1 fix)
- yaml now parses cleanly with 11 EX rules (including EX-011)
- 29 EX globs + 1 EX env (OLLAMA_MODELS) applied

## Numbers
```
yaml size:              8271 B
yaml sha:               89CA730593FF150F7B409E285FBF27FD844610CFD9D724522027AAEEBC052D6C
yaml parse:             OK (after T1 exception_rules indent fix)
EX count:               11 (EX-001 ~ EX-011)
EX globs count:         29 (parsed by reconciler)
EX envs:                ['OLLAMA_MODELS']
profile candidates:     186
drift after EX:         145  (down from 172 last measurement)
drift by target:        user=145, cloudtech=0 (CloudTech all exempt via EX-005+EX-011)
```

## Comparison
| Round | yaml_parse | EX_count | profile | drift | cloudtech_drift |
|-------|-----------|----------|---------|-------|-----------------|
| Round 8 (reported) | broken | 10 | 192 | 74 (silent drop) | included |
| Round 9 (this session prev) | broken | 10 | 197 | 172 (full re-measure) | included |
| Round 10 latest | broken | 10 | 197 | 172 (full re-measure) | included |
| **Round 10 P0 recheck (this)** | **OK** | **11** | **186** | **145** | **0** |

## Why drift dropped from 172 → 145
- yaml parses OK now → all 11 EX rules visible (was 10 before)
- EX-011 (3 CloudTech prefixes) catches D:/CloudTech-Portable/*, C:/CloudTech-Portable/*, D:/AIOS/cloudtech-saas/*
- cloudtech=0 confirms EX-005 + EX-011 cover CloudTech-Portable cleanly
- The 27 reduction = better exemption from EX rules now being read correctly

## Files
- audit/_t4_drift_recheck.json  (raw result)
- audit/2026-10-10-t4-drift-recheck.md  (this audit)

## Red lines respected
- read-only on policy (no further yaml changes)
- Same reconciler code as before (no behavior change in scan logic)
- drift is real measurement, post-yaml-fix

## Next step suggestions
- 145 still > 0; many user profiles match prohibited keywords (codex_desktop, openai.com)
- Adding more narrow EX globs (e.g., specific plugins/*.json files) could further reduce
- BUT current state is FUNCTIONAL: 4 adapter smoke OK, sha matches, EX covers CloudTech
- Don't pursue more EX reduction unless user explicitly asks - risk of breaking red lines

--- Codex supervisor - T4 drift real recheck DONE - 145 (down 27 from 172) - 2026-10-10
