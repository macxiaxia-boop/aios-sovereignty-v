# DRIFT_INCIDENT_R282_1.md — concurrent WorkBuddy relink drift (2026-09-29)

| Field | Value |
|---|---|
| Incident ID | `R282.1-drift-WorkBuddy-relink-2026-09-29` |
| Detected at | 2026-09-29 ~19:50Z (independent re-validation of R282 registry) |
| Detected by | `protocol_registry.py validate` exit 1 with 2 issues |
| Audit round | R282.1 (drift repair of R282) |
| Scope | governance pointers only; runtime drift itself out of scope |
| Status | **POINTERS FIXED (validate exit 0, list-current 29/29)** · **RUNTIME DRIFT UNFIXED** |

## 1. What changed on disk after R282 apply

R282 apply completed at 2026-09-29 ~14:53Z. The R282 `PROTOCOL_REGISTRY.json` pointed:

- `current_by_family[shared-identity-bootstrap]` → `shared-identity-bootstrap` (runtime file `_relinked/workbuddy/BOOTSTRAP.md`)
- `current_by_family[shared-identity-identity]` → `shared-identity-identity` (runtime file `_relinked/workbuddy/IDENTITY.md`)

Both files existed at R282 capture:

| Path | Size (B) | sha256 (12) | mtime |
|---|---:|---|---|
| `D:\AIOS\_relinked\workbuddy\BOOTSTRAP.md` | 1,089 | `4b154cb774c7` | 2026-09-29 |
| `D:\AIOS\_relinked\workbuddy\IDENTITY.md` | 2,745 | `084f0b7ca14d` | 2026-09-28 (byte-equal to `_agent-hub/SOUL.md`) |

At R282.1 detection (~19:50Z), an independent re-validation returned:

```
FAIL (2 issues):
  - current shared-identity-bootstrap path missing on disk: _relinked/workbuddy/BOOTSTRAP.md
  - current shared-identity-identity  path missing on disk: _relinked/workbuddy/IDENTITY.md
```

`ls _relinked/workbuddy/{BOOTSTRAP,IDENTITY}.md` → ENOENT for both. `ls -la _relinked/workbuddy/` shows the directory still contains 19 other top-level files (settings.json, workbuddy.db, mcp-tool-list.json, etc., ~1.6 MB). The junction `C:\Users\xinzh\.workbuddy → D:\AIOS\_relinked\workbuddy` is still a valid Windows Junction.

The drift is attributed to a **concurrent external process** (out of scope for the governance layer). The governance layer does NOT speculate about which WorkBuddy subsystem removed the files; it only fixes the pointer.

## 2. Pointer re-anchoring applied

| Family | R282 pointer (broken) | R282.1 pointer (working) |
|---|---|---|
| `shared-identity-bootstrap` | `shared-identity-bootstrap` → MISSING file | `r282.1-decision-shared-identity-bootstrap` → new decision record at `_agent-hub/v2/governance/decisions/R282.1_DEC_01_shared_identity_bootstrap.md` (13,304 B, sha256 `f8f412726b29…`) |
| `shared-identity-identity` | `shared-identity-identity` → MISSING file | `r282-decision-shared-identity-identity` → existing decision record at `_agent-hub/v2/governance/decisions/R282_DEC_06_shared_identity_identity.md` (11,228 B, sha256 `cf8fd1e99b4a…` — content updated in-place to reflect the drift) |

The two former runtime registry entries (`shared-identity-bootstrap`, `shared-identity-identity`) are preserved as `status=superseded` with their R282-era `hash` + `hash_size_bytes` fields kept as historical evidence. The validator skips hash checks for non-current entries, so the stale hashes do not cause `validate` failures.

### 2.1 Authority boundaries

| Decision record | Claims | Does NOT claim |
|---|---|---|
| `R282.1_DEC_01_shared_identity_bootstrap.md` | design intent (`_relinked/workbuddy/BOOTSTRAP.md` was the WorkBuddy-only bootstrap file); file existed at R282 capture (1089 B, sha256 `4b154cb7…`) | runtime availability; that the drift is fixed; that the file will reappear |
| `R282_DEC_06_shared_identity_identity.md` (updated in-place) | junction design (`install-links.ps1` lines 21-29 wire `~/.workbuddy/IDENTITY.md` → `_agent-hub/SOUL.md`); file existed at R282 capture (2745 B, sha256 `084f0b7c…`, byte-equal to SOUL.md) | runtime availability; that the drift is fixed |

## 3. Memory append blocked (separate concurrent drift)

The append-only target `_agent-hub/memory/2026-09-29.md` is **currently MISSING on disk**. The directory `D:\AIOS\_agent-hub\memory\` exists but is empty. `git status` reports the prior memory files (`2026-09-28.md`, `2026-09-29.md`, `45e357fa-…_memory.md`, `memory/automations/…`) as `AD` — added-then-deleted-in-working-tree.

This is a **separate concurrent drift** unrelated to the WorkBuddy relink. The R282.1 task scope explicitly says:

> Do NOT restore/recreate/overwrite them and do NOT alter git. Treat this as concurrent external drift and record it in a current report.

Therefore:

- The memory file is **NOT recreated**. Doing so would falsely claim the prior memory state is preserved.
- Daily memory append is **BLOCKED** for this audit round (R282.1).
- Future memory writes should go to whatever the user establishes as the new append-only target; the governance layer will not pre-create one.
- This incident is recorded here as §3, NOT in `CANONICAL_INDEX.json::memory.today` as a path (which would imply the file exists).

`CANONICAL_INDEX.json::memory.today_note` records the block without claiming the file exists:

```jsonc
"memory": {
  "today": "D:\\AIOS\\_agent-hub\\memory\\2026-09-29.md",  // pointer unchanged
  "index": "D:\\AIOS\\_agent-hub\\MEMORY.md",
  "today_note": "R282.1 (drift repair): the append-only target is currently MISSING on disk ... Do NOT recreate the file."
}
```

## 4. Files written by R282.1

| Path | Operation | Purpose |
|---|---|---|
| `_agent-hub/v2/governance/decisions/R282.1_DEC_01_shared_identity_bootstrap.md` | NEW | R282.1 decision record for shared-identity-bootstrap |
| `_agent-hub/v2/governance/decisions/R282_DEC_06_shared_identity_identity.md` | MODIFIED in-place | Updated to reflect drift; registry status promoted candidate → current |
| `_agent-hub/v2/governance/PROTOCOL_REGISTRY.json` | MODIFIED atomically via `tools/r282_1_drift_repair.py --apply --approve R282_1_REGISTRY_ONLY` | Pointer re-anchors; new entry appended; promoted entry's hash refreshed |
| `_agent-hub/v2/governance/tools/r282_1_drift_repair.py` | NEW | Drift-repair helper (dry-run default, idempotent, atomic write, post-validate) |
| `_agent-hub/v2/governance/CANONICAL_INDEX.json` | MODIFIED | Adds R282.1 entry under `governance.decisions.r282_1_records`; adds `today_note` for memory block |
| `_agent-hub/v2/reports/system-audit-20260929/PROTOCOL_AUDIT.md` | MODIFIED (append §9) | R282.1 drift section + self-check |
| `_agent-hub/v2/reports/system-audit-20260929/DRIFT_INCIDENT_R282_1.md` | NEW | This report |

## 5. Validation results (R282.1)

| Check | Result |
|---|---|
| `protocol_registry.py validate` | exit 0 — `PASS: registry valid · entries: 40 · families: 29 · current_by_family pointers: 29 / 29 (rest unresolved)` |
| `protocol_registry.py list-current` | 29/29 entries shown, 0 UNRESOLVED, 0 POINTER_BROKEN, every pointed file currently exists |
| `tools/r282_verify_decisions.py` | PASS — 7 R282 decision records: 0 mismatches, 0 pointer problems |
| Housekeeper dry-run | exit 0, counts unchanged from R282 baseline (placement_violations=100, duplicate_groups=200, bak_disabled=148, storage_threshold_breaches=0, log_rotation_candidates=0) |
| Housekeeper apply | FORBIDDEN — `--apply` exits 2 per housekeeper.py §1 |
| `CANONICAL_INDEX.json` parses | yes |
| `PROTOCOL_REGISTRY.json` parses | yes |
| All hashes for current hashable entries match | yes (all 7 R282 + 1 R282.1 decision records; the 2 `superseded` runtime entries are evidence-only, not re-hashed) |
| CloudTech repair plan unchanged | yes (`CLOUDTECH_REPAIR_PLAN.md` not touched) |
| Writes outside allowed roots | none |
| Memory recreation | none |

## 6. What this incident does NOT fix

- The WorkBuddy identity bootstrap runtime drift itself. The two files (`BOOTSTRAP.md`, `IDENTITY.md`) are still missing on disk at the close of R282.1.
- The memory drift (missing `2026-09-29.md`).
- Any other concurrent external drift that may be in progress.
- Any of the R282 deferred items (CloudTech install.cmd, `health.json` regeneration, etc.).

## 7. References

- `D:\AIOS\_relinked\workbuddy\BOOTSTRAP.md` — runtime file MISSING at R282.1 (was 1089 B, sha256 `4b154cb7…` at R282 capture).
- `D:\AIOS\_relinked\workbuddy\IDENTITY.md` — runtime file MISSING at R282.1 (was 2745 B, sha256 `084f0b7c…` at R282 capture).
- `D:\AIOS\_relinked\workbuddy\` — directory intact, 19 other top-level files (~1.6 MB).
- `C:\Users\xinzh\.workbuddy` — Windows Junction to `D:\AIOS\_relinked\workbuddy` (intact).
- `D:\AIOS\_agent-hub\install-links.ps1` — junction installer (unchanged); lines 21-29 wire `~/.workbuddy/IDENTITY.md` → `_agent-hub/SOUL.md`.
- `D:\AIOS\_agent-hub\memory\2026-09-29.md` — append-only target MISSING on disk; daily memory append blocked.
- `_agent-hub/v2/governance/PROTOCOL_REGISTRY.json` — canonical registry, post-R282.1 state.
- `_agent-hub/v2/governance/decisions/R282.1_DEC_01_shared_identity_bootstrap.md` — new R282.1 decision record (current pointer for `shared-identity-bootstrap`).
- `_agent-hub/v2/governance/decisions/R282_DEC_06_shared_identity_identity.md` — existing decision record (current pointer for `shared-identity-identity`, content updated in-place).
- `_agent-hub/v2/governance/tools/r282_1_drift_repair.py` — new drift-repair helper.
- `_agent-hub/v2/governance/CANONICAL_INDEX.json` — canonical index, gains R282.1 + memory block note.
- `_agent-hub/v2/reports/system-audit-20260929/PROTOCOL_AUDIT.md` — gains §9 R282.1 drift section.
- `_agent-hub/v2/reports/system-audit-20260929/DRIFT_INCIDENT_R282_1.md` — this report.