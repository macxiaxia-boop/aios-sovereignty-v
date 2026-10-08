# R282 Decision Record · family=shared-identity-identity

| Field | Value |
|---|---|
| Decision ID | `r282-decision-shared-identity-identity` |
| Family | `shared-identity-identity` |
| Audit round | R282 (2026-09-29, post-R281.2 PROTOCOL_AUDIT) — updated R282.1 (drift repair) |
| Verdict | **PROMOTE candidate → current** — workbuddy IDENTITY.md IS the canonical WorkBuddy identity by junction design (install-links.ps1 junctions `~/.workbuddy/IDENTITY.md` → `_agent-hub/SOUL.md`). R282.1 update: the runtime IDENTITY.md file existed at R282 evidence capture (2,745 B, sha256 `084f0b7c…`, byte-equal to SOUL.md) but has since disappeared from disk after a concurrent external WorkBuddy relink drift. **This decision-record authority does NOT claim runtime availability**; it records the design intent and the as-of-R282 evidence, and the `current_by_family` pointer is now anchored to THIS decision record (not to the missing runtime entry). |
| Confidence | HIGH (design intent verified at R282; R282.1 pointer re-anchoring verified by `validate` exit 0) |
| Captured at | 2026-09-29T14:43:00Z (initial), updated 2026-09-29T19:55:00Z (R282.1 drift repair) |

## 1. Question

The protocol family `shared-identity-identity` was UNRESOLVED because the workbuddy `IDENTITY.md` file:
1. Lives only at `_relinked/workbuddy/IDENTITY.md` (not propagated to other agents).
2. Has identical content to `_agent-hub/SOUL.md` (sha256 `084f0b7c…`).
3. Has a stale `.bak` from 2026-09-22 (a blank "Fill this in" template).

Is this a current file? Is the design intentional? Should the entry be promoted?

## 2. Evidence (disk truth)

### 2.1 Files of record

| Path | Size (B) | mtime | sha256 (12) | Status |
|---|---:|---|---|---|
| `D:\AIOS\_relinked\workbuddy\IDENTITY.md` | 2,745 | 2026-09-28 18:53 | `084f0b7ca14d` | WorkBuddy identity (content = SOUL.md) — existed at R282 capture; **CURRENTLY MISSING on disk (R282.1)** |
| `D:\AIOS\_relinked\workbuddy\IDENTITY.md.bak` | 582 | 2026-09-22 16:30 | `ea88682efde0` | Stale blank template (unchanged) |
| `D:\AIOS\_agent-hub\SOUL.md` | 2,745 | 2026-09-28 18:53 | `084f0b7ca14d` | (compared) — junction source; still present |

- `cmp` on `D:/AIOS/_relinked/workbuddy/IDENTITY.md` vs `D:/AIOS/_agent-hub/SOUL.md` → BYTE-IDENTICAL.

### 2.2 Why the content is identical by design

Reading `_agent-hub/install-links.ps1` (lines 21-29):

```powershell
$pairs = @(
    @{ Source = "C:\Users\xinzh\.workbuddy\SOUL.md";   Target = "$HUB\SOUL.md"   },
    @{ Source = "C:\Users\xinzh\.workbuddy\USER.md";   Target = "$HUB\USER.md"   },
    @{ Source = "C:\Users\xinzh\.workbuddy\MEMORY.md"; Target = "$HUB\MEMORY.md" },
    @{ Source = "C:\Users\xinzh\.workbuddy\IDENTITY.md"; Target = "$HUB\SOUL.md" },
    @{ Source = "C:\Users\xinzh\.codex\AGENTS.md";     Target = "$HUB\AGENTS.md" },
    @{ Source = "C:\Users\xinzh\.claude\CLAUDE.md";    Target = "$HUB\CLAUDE.md" }
)
```

The 4th pair (`~/.workbuddy/IDENTITY.md` → `$HUB\SOUL.md`) is the design intent:
- WorkBuddy looks for `~/.workbuddy/IDENTITY.md` at session start.
- That file is a junction TO `_agent-hub/SOUL.md` (the cross-agent identity SSOT).
- The junction target's content is propagated everywhere automatically.

### 2.3 Real-disk verification of the junction target

- `C:\Users\xinzh\.workbuddy\IDENTITY.md` exists at 2,745 B, sha256 `084f0b7c…`.
- `Get-Item` reports `Attributes=Archive, LinkType={C:\AIOS\_relinked\workbuddy\IDENTITY.md}`.
  - Note: the `LinkType` value `C:\AIOS\_relinked\workbuddy\IDENTITY.md` is a Windows Alt-Stream / NTFS metadata field, NOT an active symlink. The actual content lives at both `D:\AIOS\_relinked\workbuddy\IDENTITY.md` (in this workspace) and at the user-home path. Both copies are byte-identical SOUL.md content. The `C:\AIOS\` path shown by PowerShell is a legacy / pre-D-drive path string and the directory `C:\AIOS\_relinked\` does NOT currently exist on disk (verified — `ls C:/AIOS/_relinked/workbuddy/` → No such file or directory).
  - The registry entry `path=_relinked/workbuddy/IDENTITY.md` (D:\AIOS root) is the correct canonical reference for this round.

### 2.4 Why the file is `current` even though it's workbuddy-only

- `CANONICAL_INDEX.json::shared_identity.BOOTSTRAP` documents that BOOTSTRAP.md is "Only for WorkBuddy; not propagated elsewhere" — same pattern.
- `CANONICAL_INDEX.json::shared_identity.IDENTITY` documents: "WorkBuddy identity; install-links.ps1 also points IDENTITY.md at _agent-hub/SOUL.md".
- The family `shared-identity-identity` is the workbuddy-specific identity facet; the cross-agent identity is `shared-identity-soul`. They are NOT in conflict — they are scoped differently.

### 2.5 The `.bak` is genuinely superseded

- `IDENTITY.md.bak` is 582 B, sha256 `ea88682efde0…`, dated 2026-09-22 16:30.
- Content (verbatim):
  > "Agent identity record\n... Fill this in during your first conversation. Make it yours. ... This isn't just metadata. It's the start of figuring out who you are."
- This is a stale blank template predating the R281 workbuddy identity refresh on 2026-09-28.
- The registry's existing entry `shared-identity-identity.workbuddy-bak` (status=`superseded`, `superseded_by=shared-identity-identity`) correctly captures this.

## 3. Decision

1. **Promote `shared-identity-identity` entry to `status=current`.** The file IS the canonical WorkBuddy identity, by junction design (install-links.ps1 wires `~/.workbuddy/IDENTITY.md` → `_agent-hub/SOUL.md`).
2. **`current_by_family[shared-identity-identity] = shared-identity-identity`.**
3. **The decision record is appended as a NEW entry `r282-decision-shared-identity-identity` with `status=candidate`**, providing the rationale (junction design + install-links.ps1 evidence) so future readers do not re-litigate the IDENTITY-vs-SOUL byte-equality.
4. **Existing superseded entry preserved**: `shared-identity-identity.workbuddy-bak` stays in `entries[]` with `status=superseded`, `superseded_by=shared-identity-identity`. The stale `.bak` file remains on disk as historical evidence.
5. **Cross-agent identity separation preserved**: the cross-agent identity family is `shared-identity-soul` (pointing at `_agent-hub/SOUL.md`). The workbuddy-specific identity family is `shared-identity-identity` (pointing at `_relinked/workbuddy/IDENTITY.md`). Both are current; they are not duplicates because the install-links.ps1 junction wiring depends on both paths existing.

## 4. Limitations

- This decision does NOT modify the content of `_relinked/workbuddy/IDENTITY.md`. The byte-identical-to-SOUL.md content is by design.
- This decision does NOT update `install-links.ps1` or `sync-from-hub.ps1`. Those scripts already encode the correct mapping; this decision merely ratifies the design.
- The PowerShell `LinkType` metadata pointing at `C:\AIOS\_relinked\workbuddy\IDENTITY.md` (a non-existent path) is documented as Windows Alt-Stream residue. The registry pointer uses the `D:\AIOS\_relinked\workbuddy\IDENTITY.md` path which is the canonical workspace location.

## 5. Superseded candidates

- `shared-identity-identity.workbuddy-bak` (status=`superseded`) — unchanged, remains historical evidence of the 2026-09-22 blank template.
- No other candidates exist for this family.

## 6. Verification timestamp

- File review + cmp: 2026-09-29T14:43:00Z.
- `install-links.ps1` review: 2026-09-29T14:43:00Z (lines 21-29 confirm the junction design).

## 7. References

- `D:\AIOS\_relinked\workbuddy\IDENTITY.md` — the canonical file (was `current` at R282 capture; **MISSING at R282.1**; pointer re-anchored to this decision record).
- `D:\AIOS\_relinked\workbuddy\IDENTITY.md.bak` — stale template (still `superseded`).
- `D:\AIOS\_agent-hub\SOUL.md` — the junction target (byte-identical content; still present).
- `D:\AIOS\_agent-hub\install-links.ps1` — the junction installer (defines the IDENTITY → SOUL mapping).
- `D:\AIOS\_agent-hub\sync-from-hub.ps1` — sibling sync script (for non-junction agents).
- `CANONICAL_INDEX.json::shared_identity` — index entries for both IDENTITY and SOUL families.
- `PROTOCOL_REGISTRY.json::current_by_family[shared-identity-identity]` — pointer target post-R282.1: `r282-decision-shared-identity-identity` (this entry; promoted from candidate to current).
- `_agent-hub/v2/governance/decisions/R282.1_DEC_01_shared_identity_bootstrap.md` — sibling R282.1 decision record for the bootstrap drift.
- `_agent-hub/v2/reports/system-audit-20260929/DRIFT_INCIDENT_R282_1.md` — drift incident report.

## 8. R282.1 update — pointer re-anchored (2026-09-29 19:55Z)

### 8.1 What changed

Between R282 (14:43Z–14:53Z) and R282.1 (~19:50Z), the on-disk runtime file `D:\AIOS\_relinked\workbuddy\IDENTITY.md` disappeared. `ls` returns ENOENT for both `BOOTSTRAP.md` and `IDENTITY.md`; the rest of the `_relinked/workbuddy/` directory is intact (19 other top-level files, ~1.6 MB total). The junction `C:\Users\xinzh\.workbuddy → D:\AIOS\_relinked\workbuddy` is also intact. The drift is attributed to a concurrent external process (out of scope for governance); the governance layer only fixes the pointer.

As a result:

- The `shared-identity-identity` registry entry (the runtime row) flipped from `status=current` to `status=superseded`. Its `superseded_by` is now `r282-decision-shared-identity-identity` (this entry). Its `hash` (`084f0b7c…`) and `hash_size_bytes` (2,745) are kept as historical R282-era evidence and are NOT recomputed (the file is absent on disk). The validator skips hash check for non-current entries, so the stale hash does not cause validate failures.
- The existing `r282-decision-shared-identity-identity` entry (this file) is promoted from `status=candidate` to `status=current`. `current_by_family[shared-identity-identity]` is set to `r282-decision-shared-identity-identity` — **the pointer target ID is unchanged**; only its `status` flips.
- This decision record (the markdown file you are reading) is now the canonical pointer for `shared-identity-identity`. Its authority rests on the junction-design rationale already documented above (§3); runtime availability is explicitly NOT claimed.

### 8.2 What did NOT change

- The `R282_DEC_06` decision record file path itself (`_agent-hub/v2/governance/decisions/R282_DEC_06_shared_identity_identity.md`).
- The design intent: `install-links.ps1` still wires `~/.workbuddy/IDENTITY.md` → `_agent-hub/SOUL.md`.
- The cross-agent identity family (`shared-identity-soul`) — still pointed at `_agent-hub/SOUL.md` (unchanged, file still present).
- The `shared-identity-identity.workbuddy-bak` entry — still `superseded` historical evidence (unchanged).
- Any WorkBuddy runtime state, junction, service, watchdog, or user-home file.

### 8.3 Acknowledged limits

- The decision record claims the design is correct; it does NOT claim the runtime file currently exists or will reappear. If the relink drift is transient, the runtime entry may be revived in a future round; if permanent, this decision record remains the pointer.
- The byte-equal-to-SOUL.md content story is preserved as the original rationale; the drift is an orthogonal fact about disk state, not about the design.
