# R282 Decision Record · family=reconstruction-broken-bridges-report

| Field | Value |
|---|---|
| Decision ID | `r282-decision-reconstruction-broken-bridges-report` |
| Family | `reconstruction-broken-bridges-report` |
| Audit round | R282 (2026-09-29, post-R281.2 PROTOCOL_AUDIT) |
| Verdict | **MARK SUPERSEDED** — the bridge registry is the authoritative bridge status source; the broken-bridges report is a historical narrative ledger |
| Confidence | HIGH for document-authority ordering; the bridge registry is fresher and schema-tracked |
| Captured at | 2026-09-29T14:43:00Z |

## 1. Question

The protocol family `reconstruction-broken-bridges-report` was UNRESOLVED because the file `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BROKEN_BRIDGES.md` (R212-2026-09-26) was a `candidate` while its content disagreed with the live `AIOS_BRIDGE_REGISTRY.json` on the `br-claudecode-openclaw` status. Which file is the source of truth?

## 2. Evidence (disk truth)

### 2.1 Files of record

| Path | Size (B) | mtime | sha256 (12) | Version field | Schema-tracked? |
|---|---:|---|---|---|---|
| `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json` | 4,946 | 2026-09-29 (today, edited for R320.6 status correction) | `407c139aae53` | `R212-step4-v1` | YES (JSON, schema-tracked) |
| `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BROKEN_BRIDGES.md` | 4,307 | 2026-09-27 17:50 | `33a9e43fe9fe` | `R212-2026-09-26` | NO (narrative markdown; last update 2 days before today's registry edit) |

### 2.2 Authority ordering evidence

1. `AIOS_BRIDGE_REGISTRY.json` is referenced by:
   - `CANONICAL_INDEX.json::reconstruction_registry.bridge_registry` as the canonical sibling of `broken_bridges`.
   - `PROTOCOL_REGISTRY.json::reconstruction-bridge-registry` (family `current`).
   - `reconstruction-broken-bridges-report` entry's own `tension_with` field: `"reconstruction-bridge-registry"` (i.e. the broken-bridges report self-identifies as disagreeing with the bridge registry).
2. `AIOS_BROKEN_BRIDGES.md` is referenced by:
   - `CANONICAL_INDEX.json::reconstruction_registry.broken_bridges` as a sibling (not canonical).
   - `PROTOCOL_REGISTRY.json::reconstruction-broken-bridges-report` (family UNRESOLVED → resolved by this decision).
3. The broken-bridges report text on `br-claudecode-openclaw` (line 29-32):
   > "Status: CANDIDATE · health = unbuilt · Reason: 没有显式 bridge,需要经 AIOS 中转 · Last Success: N/A"
   This text was written when the bridge registry row was `built/partial` (R320 overclaim). After R320.1 the bridge registry row was corrected to `loopback_only/unverified`. The broken-bridges report has NOT been refreshed to match.
4. The broken-bridges report IS authoritative for the "Recently Repaired" narrative (R211 / R260 / R265) — it documents HOW bridges were diagnosed and fixed. This is a valid role for a narrative ledger, not a live authority role.

### 2.3 Live operational state (recheck 2026-09-29 14:43)

- OpenClaw daemon: PID 23700 LISTENING 127.0.0.1:18792; `/healthz` returned HTTP 000/timeout (degraded transient; see R282_DEC_01).
- V22: PID 23104 LISTENING 127.0.0.1:5099; `/health` 200 OK.
- `br-claudecode-openclaw` row text in bridge registry: matches live probe within the documented "loopback_only / unverified" caveat (no v2 inbox consumer observed for OpenClaw).

## 3. Decision

1. **`AIOS_BRIDGE_REGISTRY.json` is the document-authoritative bridge status source.** It is the SSOT for the `reconstruction-bridge-registry` family.
2. **`AIOS_BROKEN_BRIDGES.md` is the historical narrative ledger.** It documents R211/R260/R265 repair events but is NOT live authority for "what is the bridge status today".
3. **`reconstruction-broken-bridges-report` family entry → `status=superseded`**, `superseded_by=reconstruction-bridge-registry`. The file remains on disk as evidence; it is not promoted to `current` for the family because its content is not the authoritative source.
4. **The decision record IS the family pointer.** `current_by_family[reconstruction-broken-bridges-report]` is set to a new registry entry `r282-decision-reconstruction-broken-bridges-report` with `status=current`, pointing at this markdown. The new entry documents the authority ordering so that future readers do not re-litigate it.
5. **Action item (optional, not this round)**: refresh `AIOS_BROKEN_BRIDGES.md` text on `br-claudecode-openclaw` to add a note "superseded by bridge registry; see R282_DEC_01". Out of scope for R282 because the broken-bridges file is a narrative and the authority ordering is now self-evident from the registry.

## 4. Limitations

- This decision does NOT modify the `AIOS_BROKEN_BRIDGES.md` file content. It documents the authority ordering at the registry level. A future codex round can refresh the markdown if desired.
- The bridge registry's own `tension_with` metadata is preserved (it is historical evidence that this conflict existed before this decision resolved it).

## 5. Superseded candidates

- `reconstruction-broken-bridges-report` registry entry → `status=superseded` (was `candidate`); `superseded_by=r282-decision-reconstruction-broken-bridges-report`.
- The text inside `AIOS_BROKEN_BRIDGES.md` is preserved verbatim (no edits in this round).

## 6. Verification timestamp

- File review: 2026-09-29T14:43:00Z (sha256 + mtime check on both files).
- Live probe: 2026-09-29T14:43:00Z (`netstat -ano`, `curl /healthz`, `curl /health`).

## 7. References

- `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json` — authoritative SSOT (family `current`).
- `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BROKEN_BRIDGES.md` — narrative ledger (now `superseded` for authority).
- `_agent-hub/v2/governance/CANONICAL_INDEX.json::reconstruction_registry` — SSOT pointer.
- `_agent-hub/v2/CHANGELOG.md [2.0.3]` — R320.6 live round-trip evidence cited in bridge registry.
- R282_DEC_01 — sibling decision on `bridge-claudecode-openclaw` document-authority pointer.
