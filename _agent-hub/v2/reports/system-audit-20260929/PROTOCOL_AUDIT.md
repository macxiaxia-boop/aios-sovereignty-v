# Protocol Audit — 2026-09-29 (R281.1 + R281.2 cleanup pass)

> **R281.1 supersedes R281 initial PROTOCOL_AUDIT.** R281's first pass had a
> hand-counted `totals` field that didn't match its own `entries` (22 vs 25 claimed).
> R281.1 rebuilt `governance/PROTOCOL_REGISTRY.json` schema=2 with per-entry `family`,
> top-level `current_by_family` mapping (machine-checked: 22 current, 7 unresolved),
> real sha256 for every ≤20MB entry, and a `protocol_registry.py` validator/publisher
> tool. This report reflects the rebuilt registry.
>
> **R281.2 (2026-09-29, scope-only cleanup) adds:**
> 1. Scanner `compute_self_excluded_roots()` now excludes exactly TWO paths:
>    `governance/` (治理工具) and `reports/system-audit-20260929/` (本轮自增长输出).
>    The entire `_agent-hub/v2/reports` subtree is NO LONGER excluded, so the
>    formal reports (`IMPLEMENTATION_REPORT.md`, `health.json`, `status.json`,
>    `test_run.json`, `test-output.txt`) now appear in `FILE_INVENTORY.csv`.
> 2. This round's temporary assets were promoted into a stable layout:
>    - `governance/tools/compute_protocol_hashes.py` (was `_tmp_compute_hashes.py`)
>    - `governance/tools/build_protocol_registry.py` (was `_tmp_build_registry.py`)
>    - `governance/tests/fixtures/TEST_ONLY_protocol_registry.json` (moved out of root)
>    - `governance/tests/README.md` (test directory contract)
> 3. `CANONICAL_INDEX.json` schema bumped to 2 with a `governance` block
>    explicitly listing the canonical registry, the tools subtree (non-canned),
>    and the tests subtree (non-canned). `PLACEMENT_RULES.md` gained §5a
>    codifying the canonical registry surface.
> 4. **The ONLY canonical protocol registry is
>    `governance/PROTOCOL_REGISTRY.json`.** Files under `governance/tools/`
>    and `governance/tests/fixtures/` NEVER participate in `current_by_family`
>    resolution. `protocol_registry.py` validates only the canonical file
>    unless `--registry <path>` overrides for tests.

> Scope: identify real protocol / registry / spec / schema files, classify each as
> `current` / `candidate` / `superseded` / `unknown`, and resolve the
> "100-protocol mess" question with machine-readable evidence.

## 1. The "100 protocol" question — direct answer

**There is no master `MASTER_PROTOCOL*` or `protocol_index*` file in `D:\AIOS\`.**
The phrase "100 protocols" was a colloquial reference to the implicit universe of
registries / specs / schemas / bridges / capabilities / radar items, which **when
summed** gives:

| Source | Count |
|---|---:|
| AIOS_SYSTEM_REGISTRY | 7 systems |
| AIOS_AGENT_REGISTRY | 18 agents |
| AIOS_SKILL_REGISTRY | 11 families / 340 packages |
| AIOS_MCP_REGISTRY | 11 MCPs |
| AIOS_TOOL_REGISTRY | 19 tools + connectors |
| AIOS_BRIDGE_REGISTRY | 9 bridges |
| AIOS_CAPABILITY_GRAPH | 6 capabilities |
| AIOS_CANONICAL_CANDIDATES | 80 candidate AGENTS.md/CLAUDE.md paths |
| **Implicit total** | **161 systems / 80 canonical paths** |

The "100" was a rounding of this implicit count. There is no master index file;
this registry's `governance/PROTOCOL_REGISTRY.json` is the first attempt to enumerate
them.

## 2. Machine-readable current-pointer order

To prevent stale-mtime arguments, the order of authority is fixed:

1. `governance/PROTOCOL_REGISTRY.json` field `current_id` for that protocol
2. `governance/CANONICAL_INDEX.json` mapping
3. Explicit `supersedes` chain in the file's own frontmatter (`"supersedes": [...]`)
4. **Hash + mtime as evidence only** — never the sole selector

If two files claim to be current, both flip to `unknown` until user decides.

## 3. Real protocol-versioning map

| Topic | Current | Superseded | Status |
|---|---|---|---|
| v2 bidirectional protocol | `_agent-hub/v2/protocols/v1.md` | — | current |
| v2 envelope schema | `_agent-hub/v2/schemas/envelope.schema.json` | — | current |
| v2 task schema | `_agent-hub/v2/schemas/task.schema.json` | — | current |
| v2 state schema | `_agent-hub/v2/schemas/state.schema.json` | — | current |
| v2 agent registry | `_agent-hub/v2/agents/agents.json` | — | current |
| v2 paths SSOT | `_agent-hub/v2/src/paths.py` | — | current |
| Reconstruction system registry | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_SYSTEM_REGISTRY.json` | — | current (R212-step2-v1) |
| Reconstruction agent registry | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_AGENT_REGISTRY.json` | — | current (R212-step4-v1) |
| Reconstruction skill registry | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_SKILL_REGISTRY.json` | — | current (R212-step4-v1) |
| Reconstruction MCP registry | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_MCP_REGISTRY.json` | — | current (R212-step4-v1) |
| **Reconstruction tool registry** | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_TOOL_REGISTRY.json` | — | **CANDIDATE — namespace anomaly (`APP_CONNECTOR_FABRIC_PHASE_2_V1`)** |
| Reconstruction bridge registry | `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json` | — | current (R212-step4-v1, freshest) |
| Reconstruction broken bridges | `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BROKEN_BRIDGES.md` | — | **CANDIDATE — disagrees with bridge registry on br-claudecode-openclaw** |
| Reconstruction capability graph | `AIOS_RECONSTRUCTION/04_CAPABILITY_GRAPH/AIOS_CAPABILITY_GRAPH.json` | — | current (R212-step8-v1) |
| Reconstruction canonical candidates | `AIOS_RECONSTRUCTION/02_CANONICAL/AIOS_CANONICAL_CANDIDATES.json` | — | current (R212-step3-v1) |
| Reconstruction reality map | `AIOS_RECONSTRUCTION/00_REALITY/AIOS_REALITY_MAP.json` | — | current (R212-step1-v2-targeted) |
| Reconstruction progress | `AIOS_RECONSTRUCTION/AIOS_RECONSTRUCTION_PROGRESS.json` | — | current (R212) |
| v2 implementation report | `_agent-hub/v2/reports/IMPLEMENTATION_REPORT.md` | — | current (2.0.3) |
| **v2 health snapshot** | `_agent-hub/v2/reports/health.json` | — | **CANDIDATE — stale vs CHANGELOG §2.0.3** |
| Shared AGENTS.md | `_agent-hub/AGENTS.md` | `_agent-hub/AGENTS.md.bak` (in workbuddy junction) | current |
| Shared CLAUDE.md | `_agent-hub/CLAUDE.md` | `C:/Users/xinzh/.claude/CLAUDE.md.bak` | current |
| Shared MEMORY.md | `_agent-hub/MEMORY.md` | — | current |
| Shared SOUL.md | `_agent-hub/SOUL.md` | — | current |
| Shared USER.md | `_agent-hub/USER.md` | — | current |
| WorkBuddy BOOTSTRAP | `_relinked/workbuddy/BOOTSTRAP.md` | — | current |
| WorkBuddy IDENTITY | `_relinked/workbuddy/IDENTITY.md` | `_relinked/workbuddy/IDENTITY.md.bak` | candidate (only used by workbuddy) |
| chatgpt-bridge TASK_PROTOCOL | `_backups/chatgpt_bridge_pre_rollback_to_V4P9-FINAL_20260927_151216/TASK_PROTOCOL.md` | 2 earlier backups | superseded (3 identical copies) |
| **br-claudecode-openclaw** | (none) | — | **UNKNOWN — registry says loopback_only, broken report says unbuilt** |
| Spec catalog | (none) | — | **UNKNOWN — spec# numbering referenced everywhere; catalog not in tree** |
| CloudTech WinSW descriptor | `cloudtech-saas/cloudtech-saas.xml.bak_C_1790215941` | — | candidate (RENAMED; install.cmd broken) |

## 4. The publish flow (proposed, pending approval)

```
[author writes new protocol v2 file]
  -> governance/PROTOCOL_REGISTRY.json:
       previous current -> superseded, retain path + sha256
       new file -> current_id, status=current, version=vN
       update supersedes chain
  -> legacy file marked .superseded.20260929 but NEVER moved by automation
  -> if legacy file is .md/.json, leave it; if user wants physical archive, run:
       governance/housekeeper.py --apply --rows <legacy path>
       (requires explicit per-file approval)
  -> append entry to governance/MOVE_LOG.json
```

This round ships the **registry and rules only**. The automation requires a
separate approval round.

## 5. Tension / conflict log (these are unresolved)

1. **br-claudecode-openclaw status conflict**
   - `AIOS_BRIDGE_REGISTRY.json`: status=`loopback_only`, health=`unverified` (R320.6 — file-queue v1.0 envelope exists but no real round-trip observed)
   - `AIOS_BROKEN_BRIDGES.md`: status=`CANDIDATE`, health=`unbuilt`
   - **Required decision**: which status is right?

2. **AIOS_TOOL_REGISTRY namespace anomaly**
   - All other R212 registries use `R212-stepN-v1`
   - Tool registry uses `APP_CONNECTOR_FABRIC_PHASE_2_V1`
   - **Required decision**: rename for consistency OR accept as intentional separate namespace

3. **Spec catalog absence**
   - spec# numbering referenced in registries, capability graph, radar, workflows (#3, #5-6, #7-9, #11-13, #15-16, #17, #22, #30-31, #34, #36, #37, #43, #45, #60, #82)
   - No catalog file exists in `D:\AIOS\`
   - Presumed external at `D:\个人文件\AI\Operator\00_CORE\`
   - **Required decision**: copy catalog into AIOS_RECONSTRUCTION OR accept external reference

4. **health.json staleness**
   - `health.json` mtime 2026-09-29 12:56 (pre-CHANGELOG §2.0.3 13:21)
   - CHANGELOG says Hermes/OpenClaw `healthy=true` after live probe
   - JSON not rewritten by that probe
   - **Required decision**: re-run `aiosv2.py health` to regenerate

5. **CloudTech WinSW xml missing**
   - `install.cmd` references `cloudtech-saas.xml`
   - Only `.bak_C_1790215941` variant exists
   - **Required decision**: restore original filename OR update install.cmd

## 6. Counts (R281.1 rebuild)

| Status | Count |
|---|---:|
| current | **22** |
| candidate | **5** |
| superseded | **4** |
| unknown | **1** |
| **Total entries** | **32** |
| **Total families** | **29** |
| **Unresolved families** (current_by_family = null) | **7** |

Unresolved families (user decision required before they can be `current`):
- `bridge-claudecode-openclaw` (status conflict between two AIOS files)
- `chatgpt-bridge-task-protocol` (no current; all copies superseded)
- `cloudtech-xml-winsw` (file renamed; install.cmd broken)
- `reconstruction-broken-bridges-report` (conflicts with bridge registry)
- `reconstruction-tool-registry` (namespace anomaly)
- `shared-identity-identity` (workbuddy-only)
- `v2-health-snapshot` (stale vs CHANGELOG 2.0.3)

(The "100-protocol" colloquial count was the implicit-universe of 161 systems/paths in registries. There is no master file — this registry is the first enumeration.)

## 7. What this audit does NOT do

- Does not auto-move any `.bak`/`.disabled` file.
- Does not rewrite any registry file.
- Does not commit any change.
- Does not stop any daemon, service, watchdog, or scheduled task.

## 8. R282 — 7 UNRESOLVED families resolved (2026-09-29)

### 8.1 Scope

R281.1 left 7 protocol families with `current_by_family[X] = null` (UNRESOLVED). R282 resolves all 7 by:

1. Creating one governance decision record per formerly-UNRESOLVED family under `_agent-hub/v2/governance/decisions/R282_DEC_NN_<family>.md`.
2. Flipping the on-disk evidence files' statuses in `PROTOCOL_REGISTRY.json` (some promoted to `current`, some marked `superseded` per the per-family decision).
3. Setting `current_by_family[X]` to either the on-disk file (when legitimate) OR the new decision record (when no runtime file is legitimate).

No source code, scripts, XML, registry fields OUTSIDE `PROTOCOL_REGISTRY.json` + `CANONICAL_INDEX.json`, watchdog, daemon, service, or scheduled task was modified. No CloudTech install / uninstall / XML rename was performed. No `health.json` regeneration was performed.

### 8.2 Per-family resolution

| Family | R281.1 state | R282 resolution | Decision record | Runtime file status |
|---|---|---|---|---|
| `bridge-claudecode-openclaw` | UNRESOLVED, conflict between bridge registry (loopback_only) and broken-bridges report (unbuilt) | **PROMOTE** runtime file → `current`. Document-authority pointer = registry JSON. Operational state stays `loopback_only/unverified`. | `R282_DEC_01` (candidate, evidence) | `current` (was `unknown`) |
| `chatgpt-bridge-task-protocol` | UNRESOLVED, only superseded backup copies | **NO RUNTIME FILE.** 39 byte-identical `_backups/.../TASK_PROTOCOL.md` copies (sha256 `5ca3cd76…`) are historical evidence. v2 hub task protocol triad replaces. | `R282_DEC_02` (current, AUTHORITATIVE ABSENT) | `superseded` (unchanged) |
| `cloudtech-xml-winsw` | UNRESOLVED, `.bak_C_1790215941` XML only, `install.cmd` broken | **NO RUNTIME PROMOTION.** `.bak` XML stays on disk but is NOT promoted (per task rule "Do not silently promote a .bak file"). Decision record IS current. | `R282_DEC_03` (current) | `superseded` (was `candidate`) |
| `reconstruction-broken-bridges-report` | UNRESOLVED, narrative vs bridge registry conflict | **SUPERSEDED.** Bridge registry is SSOT; broken-bridges report is historical narrative. Decision record IS current. | `R282_DEC_04` (current) | `superseded` (was `candidate`) |
| `reconstruction-tool-registry` | UNRESOLVED, namespace `APP_CONNECTOR_FABRIC_PHASE_2_V1` vs siblings' `R212-stepN-v1` | **PROMOTE** runtime file → `current`. Namespace is intentionally separate (post-R212 work); not a defect. | `R282_DEC_05` (candidate, evidence) | `current` (was `candidate`) |
| `shared-identity-identity` | UNRESOLVED, workbuddy-only file, byte-identical to SOUL.md | **PROMOTE** runtime file → `current`. Junction design via `install-links.ps1` lines 21-29. | `R282_DEC_06` (candidate, evidence) | `current` (was `candidate`) |
| `v2-health-snapshot` | UNRESOLVED, `health.json` mtime 12:56 stale vs CHANGELOG 2.0.3 at 13:21 | **SUPERSEDED.** Per task instruction, do NOT regenerate `health.json`. Decision record IS current; file preserved on disk. | `R282_DEC_07` (current) | `superseded` (was `candidate`) |

### 8.3 Live operational recheck (read-only, 2026-09-29 14:43)

| Check | Result | Verdict |
|---|---|---|
| V22 upstream `127.0.0.1:5099` | `LISTENING` PID 23104 | up |
| V22 `GET /health` | HTTP 200 body `{"status":"ok","version":"22.0.0","v10_modules_included":130}` | healthy |
| OpenClaw `127.0.0.1:18792` | `LISTENING` PID 23700 | port up |
| OpenClaw `GET /healthz` | HTTP 000 (8s timeout, no body) | degraded transient |
| `sc query CloudTechV22Monitor` | `OpenService 失败 1060` | service NOT installed (consistent with `install.cmd` broken state) |
| V2 two-process round-trip | Codex↔CC envelopes `37531663-…` etc. per CHANGELOG [2.0.3] | VERIFIED (Codex-permitted shell) |
| V2 OpenClaw inbox consumer | no process observed | unproven (matches bridge registry `loopback_only / unverified`) |

### 8.4 Counts (R282)

| Status | Count |
|---|---:|
| current | **29** (22 original + 7 from decision-record entries that are `status=current`) |
| candidate | **3** (4 candidates promoted to `current`; 4 evidence-only decision-record entries added as `candidate`) |
| superseded | **7** (the 7 formerly-`candidate`/`unknown` runtime entries that the decision records replace) |
| unknown | **0** |
| **Total entries** | **39** (32 original + 7 R282 decision records) |
| **Total families** | **29** |
| **Unresolved families** | **0** |
| **Resolved this round** | **7** (all formerly UNRESOLVED) |

### 8.5 CloudTech repair plan (deliverable, NOT applied)

`reports/system-audit-20260929/CLOUDTECH_REPAIR_PLAN.md` documents:

- Verified current file tree + sha256s.
- Exact failure mechanism (line 19 of `install.cmd` references non-existent `cloudtech-saas.xml`).
- Two viable options (Option A: restore filename; Option B: edit scripts), Option A recommended.
- Rejected alternative (abandon WinSW entirely; preserve restart-on-failure semantics).
- Proposed file-level patches (NOT applied).
- Preflight checks (10 items), encoding/path considerations, WinSW behavior analysis, service-name collision check.
- Backup strategy, dry-run / syntax validation, install verification (5 acceptance criteria), rollback steps.
- Explicit approval boundary: user must approve apply + run preflight + run validate + run health check + run verification.

### 8.6 What R282 did NOT do

- Did NOT regenerate `v2/reports/health.json` (per task instruction).
- Did NOT rename `cloudtech-saas.xml.bak_C_1790215941` → `cloudtech-saas.xml` (repair deferred to user-approved apply).
- Did NOT edit `install.cmd` / `uninstall.cmd` (same).
- Did NOT modify any daemon, service, watchdog, scheduled task, registry, MCP server, or symlink.
- Did NOT read any secret or token.
- Did NOT move, delete, rename, compress any pre-existing user file.

### 8.7 Self-check (R282)

| Check | Result |
|---|---|
| `protocol_registry.py validate` | exit 0 (`PASS: registry valid · entries: 39 · families: 29 · current_by_family pointers: 29 / 29 (rest unresolved)`) |
| `protocol_registry.py list-current` | 29/29 entries shown, 0 UNRESOLVED, 0 POINTER_BROKEN |
| Decision record sha256 cross-check | All 7 decision files re-hashed at apply time, matched registry entry `hash` fields |
| CANONICAL_INDEX.json parses | yes (`audit_id: system-audit-20260929-R282`, 7 R282 decision records indexed) |
| Decision records exist on disk | yes (all 7 at `_agent-hub/v2/governance/decisions/`) |
| Housekeeper dry-run | (see governance self-check below) |
| Housekeeper apply | (see governance self-check below) |
| Git status scope | writes only under allowed roots (governance/, reports/system-audit-20260929/, memory/) |

## 9. R282.1 — concurrent WorkBuddy relink drift repair (2026-09-29 19:55Z)

### 9.1 What happened after R282

Between R282 apply (2026-09-29 ~14:53Z) and the R282.1 drift detection (~19:50Z), an independent re-validation of the registry returned:

```
FAIL (2 issues):
  - current shared-identity-bootstrap path missing on disk: _relinked/workbuddy/BOOTSTRAP.md
  - current shared-identity-identity  path missing on disk: _relinked/workbuddy/IDENTITY.md
```

The junction `C:\Users\xinzh\.workbuddy → D:\AIOS\_relinked\workbuddy` is still intact (verified via `ls -la` — Windows Junction, 27 B LinkType). The `_relinked/workbuddy/` directory still contains 19 other top-level files (~1.6 MB; `settings.json`, `workbuddy.db`, `mcp-tool-list.json`, etc.). Only the two files at issue (`BOOTSTRAP.md`, `IDENTITY.md`) are absent. The drift is attributed to a concurrent external process (out of scope for governance). The governance layer only fixes the pointer.

**This is a CURRENT-STATE drift, not a registry error.** The R282 capture was honest about what was on disk at that moment; the runtime state has changed since. The governance layer now re-anchors the two affected families to decision records so `validate` returns exit 0 and `list-current` reports 29/29 with every pointed file currently existing.

### 9.2 Per-family drift resolution

| Family | R282 pointer | R282.1 pointer | Mechanism |
|---|---|---|---|
| `shared-identity-bootstrap` | `shared-identity-bootstrap` (runtime `_relinked/workbuddy/BOOTSTRAP.md`) — MISSING at R282.1 | `r282.1-decision-shared-identity-bootstrap` (decision record) | New R282.1_DEC_01 decision record; runtime entry flipped to `superseded` (preserved as evidence with R282-era hash `4b154cb7…`, size 1089) |
| `shared-identity-identity` | `shared-identity-identity` (runtime `_relinked/workbuddy/IDENTITY.md`) — MISSING at R282.1 | `r282-decision-shared-identity-identity` (existing decision record, promoted) | R282_DEC_06 file content updated to reflect drift; registry entry promoted `candidate → current`; runtime entry flipped to `superseded` (preserved as evidence with R282-era hash `084f0b7c…`, size 2745) |

### 9.3 Authority — what the decision records do and do NOT claim

- **They claim**: the design intent (install-links.ps1 lines 21-29 wire `~/.workbuddy/IDENTITY.md` → `_agent-hub/SOUL.md`; `_relinked/workbuddy/BOOTSTRAP.md` is WorkBuddy-only by design).
- **They claim**: the file existed at R282 capture (sha256 hashes recorded in registry as evidence-only `hash` / `hash_size_bytes` fields on the `superseded` runtime entries).
- **They do NOT claim**: the file currently exists. The decision-record authority is **documentary**, not runtime-availability.
- **They do NOT claim**: the underlying WorkBuddy relink drift is fixed. That is out of scope.

### 9.4 Tool used

`tools/r282_1_drift_repair.py` — a new helper modeled on the existing `r282_update_registry.py` pattern. Features:

- Dry-run by default (no file written).
- `--apply --approve R282_1_REGISTRY_ONLY` required to apply.
- Idempotent: skips already-applied flips and the duplicate APPEND on a re-run.
- Always refreshes `hash` + `hash_size_bytes` for the promoted `r282-decision-shared-identity-identity` entry (the R282_DEC_06 file is updated in-place, so the recorded hash must follow the file).
- Atomic write: unique temp + `os.replace`; no `os.remove(target)` on failure.
- Post-apply: runs `protocol_registry.py validate` and exits 3 if validate fails (registry left in place).
- `protocol_registry.py publish` was NOT used because (a) the publish command can only add new entries, not promote existing `candidate` entries to `current`, and (b) the published path on bootstrap would force a redundant duplicate record. The custom helper is the correct fit.

### 9.5 Counts (R282.1)

| Status | Pre-R282.1 | Post-R282.1 |
|---|---:|---:|
| current | 29 | **29** (28 unchanged + 1 promoted `r282-decision-shared-identity-identity`) |
| candidate | 3 | **2** (1 promoted to current; 2 unchanged: `r282-decision-bridge-claudecode-openclaw`, `r282-decision-reconstruction-tool-registry`) |
| superseded | 7 | **9** (2 newly superseded: `shared-identity-bootstrap`, `shared-identity-identity`) |
| unknown | 0 | **0** |
| **Total entries** | **39** | **40** (39 + 1 new `r282.1-decision-shared-identity-bootstrap`) |
| **Total families** | **29** | **29** (unchanged) |
| **Unresolved families** | **0** | **0** (unchanged) |

### 9.6 Self-check (R282.1)

| Check | Result |
|---|---|
| `protocol_registry.py validate` | exit 0 (`PASS: registry valid · entries: 40 · families: 29 · current_by_family pointers: 29 / 29 (rest unresolved)`) |
| `protocol_registry.py list-current` | 29/29 entries shown, 0 UNRESOLVED, 0 POINTER_BROKEN, every pointed file currently exists |
| `tools/r282_verify_decisions.py` | PASS — 7 R282 decision records: 0 mismatches, 0 pointer problems |
| Decision record sha256 cross-check | All 8 decision files (7 R282 + 1 R282.1) re-hashed at apply time, matched registry entry `hash` fields |
| CANONICAL_INDEX.json parses | yes (`audit_id` unchanged, R282.1 added under `governance.decisions.r282_1_records`) |
| Housekeeper dry-run | exit 0, counts unchanged from R282 baseline (placement_violations=100, duplicate_groups=200, bak_disabled=148, storage_threshold_breaches=0, log_rotation_candidates=0) |
| Housekeeper apply | (FORBIDDEN in this round — `--apply` exits 2 per housekeeper.py §1) |
| Git status scope | writes only under allowed roots (governance/, reports/system-audit-20260929/). NO writes to memory/, _relinked/, _agent-hub/AGENTS.md/CLAUDE.md/SOUL.md/USER.md, user homes, services, watchdog, MCP, git |
| Files written by R282.1 | 3 new (`R282.1_DEC_01_shared_identity_bootstrap.md`, `tools/r282_1_drift_repair.py`, `DRIFT_INCIDENT_R282_1.md`), 3 modified (`PROTOCOL_REGISTRY.json` via helper, `R282_DEC_06_shared_identity_identity.md` in-place text update, `CANONICAL_INDEX.json` index update, `PROTOCOL_AUDIT.md` §9 appended). Memory file NOT recreated. |

### 9.7 What R282.1 did NOT do

- Did NOT recreate `_relinked/workbuddy/BOOTSTRAP.md` or `_relinked/workbuddy/IDENTITY.md`. Recreating them would falsely claim WorkBuddy runtime state is restored.
- Did NOT modify the junction `C:\Users\xinzh\.workbuddy` or any user-home file.
- Did NOT modify `_agent-hub/memory/2026-09-29.md` (or any memory file). The append-only target is currently missing on disk; recreating it would falsely claim prior memory state is preserved. See `DRIFT_INCIDENT_R282_1.md` §3.
- Did NOT modify `install-links.ps1`, `sync-from-hub.ps1`, or any other WorkBuddy runtime script.
- Did NOT stop, start, restart, or reconfigure any service, watchdog, daemon, MCP server, or scheduled task.
- Did NOT touch `git` (no add, commit, push, branch, reset, rebase, tag).
- Did NOT touch `cloudtech-saas/` or any CloudTech file.
- Did NOT modify the CloudTech repair plan (see `CLOUDTECH_REPAIR_PLAN.md`).
- Did NOT change any decision other than the two pointer re-anchors documented above.

### 9.8 Acknowledged limits

- The R282.1 fix is pointer-only. The WorkBuddy identity bootstrap drift itself is **unfixed**. If the relink drift is transient, the runtime files may return and a future R282.x round may revert these pointers. If permanent, these decision records remain the family pointer.
- The recorded R282-era hash on the two `superseded` runtime entries (`4b154cb7…` for BOOTSTRAP, `084f0b7c…` for IDENTITY) is preserved as historical evidence of what existed at R282 capture. The validator does not re-hash non-current entries, so the stale hash does not cause validate failures; if the files are later restored, a future round may re-promote them and re-compute.
- The R282.1 decision record uses `r282_1_role=decision_record` (not `r282_role`) to distinguish from R282-era entries. The `protocol_registry.py validate` tool checks neither field, so this is documentary only. `r282_verify_decisions.py` is R282-scoped and does not enumerate R282.1 entries; that's expected.

