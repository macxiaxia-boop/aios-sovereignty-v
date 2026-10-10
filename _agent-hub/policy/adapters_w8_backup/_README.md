# _w8_backup — historical W8 policy adapter implementations

> **Status**: KEEP (per 2026-10-10 P2 decision, codex audit `audit/2026-10-10-P2-w8-decision.md`)
> **Author**: Codex supervisor (decision on 2026-10-10)
> **撤销成本**: 极低 (1 个 cp 命令)

## Reasons to keep (not delete)
1. **67 KB total** - negligible disk cost
2. **Reference implementation** - W8 versions document the "full feature set" for 4 adapter runtimes (validate_signature, prohibited_keyword_check, etc.)
3. **Diff comparison available** - future change to current adapter can be checked against W8 for regression
4. **Revert path open** - if policy/governance requirements change and W8 features are needed, easy restore
5. **Audit memory** - these versions were committed by AIPM_FOUNDATION_02 D5 stage; deleting them erases audit trail

## What is here
- codex_runtime.py          17764 B  (original W8 codex implementation)
- claude_code_runtime.py    16044 B  (original W8 claude-code implementation)
- hermes_runtime.py         17846 B  (original W8 hermes implementation)
- openclaw_runtime.py       15859 B  (original W8 openclaw implementation)

## Why replaced
- 2026-10-10 T2 EXT-D recovery batch applied EXT-D design (singleton + 30s cache + sha256 validate + fail-soft)
- New versions: 880-892 B (18x smaller)
- All 4 new versions import from `policy/adapters_registry.py` (shared)
- Verified 4/4 adapters pass `verify_ext_d.py`

## Verification date
- Last verified: 2026-10-10 (round 10 P0 recovery)

## Restore command (if needed)
```powershell
Copy-Item D:\AIOS\_agent-hub\policy\adapters_w8_backup\*.py D:\AIOS\_agent-hub\policy\adapters\
Remove-Item D:\AIOS\_agent-hub\policy\adapters_registry.py
```
Then run `python scripts/verify_ext_d.py` to confirm W8 also works in this codebase (may need adapter spec adjustments).

## Will-delete trigger
None currently. Only delete if user explicitly orders cleanup, or if 12-month time-based cleanup policy is added (not active today).

--- Codex supervisor - W8 backup 保留决策 - 2026-10-10
