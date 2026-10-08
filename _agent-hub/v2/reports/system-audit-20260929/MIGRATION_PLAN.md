# Migration Plan — 2026-09-29 (R281.2)

> **R281.2 supersedes R281.1 MIGRATION_PLAN** with a scope-only cleanup pass:
> scanner self-exclusion narrowed from 2 broad roots to 2 precise paths, and
> this round's temporary governance assets promoted into a stable layout
> (`governance/tools/`, `governance/tests/fixtures/`). Zero user files
> deleted, zero user files moved; only newly-created governance test/aux
> assets were reorganized.
>
> **R281.1 supersedes R281 initial MIGRATION_PLAN** with corrected numbers and a new
> P0 hardening section (machine-checkable protocol pointer + housekeeper exit codes).

> Scope: forward path from current state to governed state. This is a **plan**, not an
> action. Every step that mutates state requires explicit user approval in a separate round.

## 1. What this round shipped (zero-deletion, zero-move)

| Asset | Path | Purpose |
|---|---|---|
| Scanner | `D:\AIOS\_agent-hub\v2\governance\scan_inventory.py` | Streaming metadata scanner; R281.2 self-excludes EXACTLY `_agent-hub/v2/governance` + `_agent-hub/v2/reports/system-audit-20260929` (was 2 broad roots in R281.1) |
| Asset builder | `D:\AIOS\_agent-hub\v2\governance\build_assets.py` | Reads CSV → writes summary/duplicates/hotspots reports; R281.2 narrowed self-excluded-roots prose to match scanner |
| Housekeeper | `D:\AIOS\_agent-hub\v2\governance\housekeeper.py` | R281.1: explicit `--dry-run` (default), `--apply` always exit 2; atomic write no `os.remove(target)` |
| Protocol registry | `D:\AIOS\_agent-hub\v2\governance\PROTOCOL_REGISTRY.json` | R281.1 schema=2: 32 entries with `family`, top-level `current_by_family` (22 current + 7 unresolved), real sha256 for ≤20MB entries |
| Protocol validator | `D:\AIOS\_agent-hub\v2\governance\protocol_registry.py` | R281.1 NEW: `validate` / `list-current` / `publish` (publish default dry-run; apply needs `--apply --approve REGISTRY_ONLY`) |
| Tools subdir | `D:\AIOS\_agent-hub\v2\governance\tools\` | R281.2 NEW: `compute_protocol_hashes.py` + `build_protocol_registry.py` (promoted from `_tmp_*`) |
| Tests subdir | `D:\AIOS\_agent-hub\v2\governance\tests\` | R281.2 NEW: `fixtures/TEST_ONLY_protocol_registry.json` + `README.md` |
| Placement rules | `D:\AIOS\_agent-hub\v2\governance\PLACEMENT_RULES.md` | Future file placement standard; R281.2 added §5a "canonical registry surface" |
| Canonical index | `D:\AIOS\_agent-hub\v2\governance\CANONICAL_INDEX.json` | Where shared identity, v2 stack, projects, audit live; R281.2 schema=2 with `governance` block |
| Retention policy | `D:\AIOS\_agent-hub\v2\governance\RETENTION_POLICY.md` | Per-category retention + protected types |
| Cleanup candidates | `D:\AIOS\_agent-hub\v2\governance\CLEANUP_CANDIDATES.json` | List-only, user-approved per-row |
| Audit report dir | `D:\AIOS\_agent-hub\v2\reports\system-audit-20260929\` | 10 reports + CSV + checkpoint (R281.2) |
| Memory append | `D:\AIOS\_agent-hub\memory\2026-09-29.md` | R281 + R281.1 + R281.2 entries |

## 2. Phases forward (each requires explicit user approval)

### Phase M0 — Decision point (this round's outputs)

| Decision | Owner | Why now |
|---|---|---|
| Which status is correct for `br-claudecode-openclaw` (loopback_only vs unbuilt)? | user | two AIOS-authored files disagree |
| Should `AIOS_TOOL_REGISTRY.json` be renamed from `APP_CONNECTOR_FABRIC_PHASE_2_V1` to `R212-step5-v1`? | user | namespace anomaly |
| Where does the canonical `spec#` catalog live? | user | 30+ spec references scattered; catalog missing |
| Should `_agent-hub/v2/reports/health.json` be regenerated? | user | stale vs CHANGELOG §2.0.3 |
| How to fix `cloudtech-saas/cloudtech-saas.xml` (rename restore vs install.cmd fix)? | user | install.cmd broken out-of-box |
| Approve moving `_backups/chatgpt_bridge_pre_rollback_*/TASK_PROTOCOL.md` (3 copies) to archive? | user | duplicate copies |

### Phase M1 — Apply cleanup candidates (DRY-RUN → APPLY)

Pre-conditions: M0 decisions taken.

```
# Step 1: review
python _agent-hub/v2/governance/housekeeper.py \
    --inventory _agent-hub/v2/reports/system-audit-20260929/FILE_INVENTORY.csv \
    --out      _agent-hub/v2/governance/HOUSEKEEPER_REPORT.json

# Step 2: per-row approval
# (user reviews HOUSEKEEPER_REPORT.json + CLEANUP_CANDIDATES.json)

# Step 3: APPLY (only after user signs off)
python _agent-hub/v2/governance/housekeeper.py --apply \
    --rows path1 path2 path3 ...
# (currently disabled — see RETENTION_POLICY.md §5)
```

### Phase M2 — Move legacy `_archived_*/` and `_backups/` to `archive/`

Pre-conditions: M1 done.

```
D:\AIOS\_archived_2026-09-18\            -> D:\AIOS\archive\legacy\_archived_2026-09-18\
D:\AIOS\_archived_20260925_P0\           -> D:\AIOS\archive\legacy\_archived_20260925_P0\
D:\AIOS\_archived_20260925_R259_…\       -> D:\AIOS\archive\legacy\_archived_20260925_R259_…\
D:\AIOS\_backups\chatgpt_bridge_…\       -> D:\AIOS\archive\chatgpt-bridge-rollbacks\…
D:\AIOS\_backup_aios_exe_…\              -> D:\AIOS\archive\aios-exe-snapshots\…
D:\AIOS\_r274_install_backup\            -> D:\AIOS\archive\r274-install-backup\
```

Each move writes a row to `governance/MOVE_LOG.json`.

### Phase M3 — Re-home running log sprawl

Current state: `.log`, `.pid`, `.state.json` files scattered across `D:\AIOS\` root.

```
D:\AIOS\_*.log                           -> D:\AIOS\logs\aios\<original-name>.log
D:\AIOS\_*.pid                           -> D:\AIOS\runs\live\<original-name>.pid
D:\AIOS\_*.state.json                    -> D:\AIOS\runs\live\<original-name>.state.json
```

Symlinks back at original paths for compatibility (so existing scripts keep working).

### Phase M4 — Compress and index `_workzone/` (500 MB hotspot)

`D:\AIOS\_workzone\` is the largest non-cache dir (500 MB). Many files are:
- `__pycache__/` (~already excluded by scanner)
- `*.pyc` (already excluded)
- legacy project versions (e.g. `_archived_R_A01_20260922/`)
- audit_orphan_md artifacts (`_audit_orphan_md/`)

Decision needed before compress:
- compress `_workzone/_archived_R_A01_20260922/` to `archive/workzone/_archived_R_A01_20260922.tar.zst`
- keep `_workzone/src/` live
- move logs under `_workzone/_aios_*/logs/` to `logs/workzone/`

### Phase M5 — Re-house CloudTech under `projects/`

```
D:\AIOS\cloudtech-saas\                   -> D:\AIOS\projects\cloudtech\
D:\AIOS\cloudtech-saas\cloudtech-saas.xml -> D:\AIOS\projects\cloudtech\cloudtech-saas.xml
D:\AIOS\cloudtech-saas\logs\              -> D:\AIOS\projects\cloudtech\logs\
```

This requires:
1. Fixing `cloudtech-saas.xml` filename (or install.cmd reference)
2. Updating install.cmd / uninstall.cmd / start_v22_watchdog.bat to point to new location
3. Re-installing the WinSW service

Out of scope: changing `_workzone/src/_aios_cloudtech_bridge.py` (still referenced).

## 3. What this round did NOT touch (and won't without approval)

- `D:\AIOS\aios_tasks\`, `D:\AIOS\daemons_v2\`, `D:\AIOS\_scripts\`, `D:\AIOS\_tools\`,
  `D:\AIOS\_out\`, `D:\AIOS\_patches\`, `D:\AIOS\_backups\`, `D:\AIOS\_archived_*/`,
  `D:\AIOS\_dr_v3.0_uncompressed_workspace\`, `D:\AIOS\_e_drive_dedup_workspace\`,
  `D:\AIOS\_r274_install_backup\`, `D:\AIOS\_capability\`, `D:\AIOS\_workzone\`,
  `D:\AIOS\wmic_forensics\` — all remain as-is. New work in those zones is discouraged
  (PLACEMENT_RULES.md) but existing files are untouched.
- `D:\AIOS\.git/` — git history preserved. No `git add/commit/reset/checkout/clean` performed.
- `D:\AIOS\aios_tools`, `D:\AIOS\aios_venv` symlinks — operator workspace, NEVER modify.
- `C:\Users\xinzh\Desktop` and `D:\Desktop\` — junction preserved. No files moved to desktop.
- `C:\Users\xinzh\.codex\`, `.claude\`, `.workbuddy\`, `.hermes\` — agent homes, junction preserved.
- Any secret/token/key file — never read, never reported, never modified.
- Any daemon, service, watchdog, scheduled task — none started, stopped, or modified.
- Any MCP config (`.mcp.json`, `.mcp-secrets.json`) — unchanged.

## 4. Completion matrix (this round)

| Deliverable | Status | Evidence |
|---|---|---|
| `governance/PLACEMENT_RULES.md` | ✅ shipped | file exists |
| `governance/PROTOCOL_REGISTRY.json` | ✅ shipped | 32 entries, JSON parses |
| `governance/CANONICAL_INDEX.json` | ✅ shipped | file exists, JSON parses |
| `governance/RETENTION_POLICY.md` | ✅ shipped | file exists |
| `governance/CLEANUP_CANDIDATES.json` | ✅ shipped | file exists, JSON parses |
| `governance/housekeeper.py` (dry-run) | ✅ shipped | `--dry-run` runs, `--apply` errors out |
| `reports/system-audit-20260929/INVENTORY_SUMMARY.md` | ✅ shipped | file exists |
| `reports/system-audit-20260929/DUPLICATE_ANALYSIS.md` | ✅ shipped | file exists |
| `reports/system-audit-20260929/PROTOCOL_AUDIT.md` | ✅ shipped | file exists |
| `reports/system-audit-20260929/CLOUDTECH_PROJECT_MAP.md` | ✅ shipped | file exists |
| `reports/system-audit-20260929/DESKTOP_AUDIT.md` | ✅ shipped | file exists |
| `reports/system-audit-20260929/AGENT_FOOTPRINTS.md` | ✅ shipped | file exists |
| `reports/system-audit-20260929/STORAGE_HOTSPOTS.md` | ✅ shipped | file exists |
| `reports/system-audit-20260929/MIGRATION_PLAN.md` | ✅ shipped | this file |
| `reports/system-audit-20260929/AUDIT_MANIFEST.json` | ✅ shipped | file exists, JSON parses |
| `reports/system-audit-20260929/FILE_INVENTORY.csv` | ✅ shipped | 71,799 rows, ~35.8 MB (37,518,323 bytes measured) |
| `reports/system-audit-20260929/SCAN_CHECKPOINT.json` | ✅ shipped | file exists |
| `memory/2026-09-29.md` | ✅ shipped | R281 + R281.1 + R281.2 (and R281.3 doc-consistency repair) appended |
| **0 files deleted** | ✅ | n/a |
| **0 pre-existing user files moved** | ✅ | 3 current-round generated helper/test assets reorganized (2 `_tmp_*.py` → `governance/tools/`, 1 `TEST_ONLY_*.json` → `governance/tests/fixtures/`) |
| **0 git operations** | ✅ | n/a |
| **0 daemon/service/watchdog changes** | ✅ | n/a |
| **0 secret reads** | ✅ | n/a |

## 5. Risk register for forward phases

| Risk | Severity | Mitigation |
|---|---|---|
| Loss of context if user restarts CC between M0 and M1 | low | M0 decisions are recorded in PROTOCOL_AUDIT.md §5; can be re-read |
| Housekeeper `--apply` misimplemented (e.g., deletes instead of moves) | high | Dry-run only this round; apply requires separate approval + tests |
| `_workzone` compress breaks live `_aios_cloudtech_bridge.py` import | high | Phase M4 includes dry-run + import smoke test before compress |
| Agent home junctions broken | medium | Junction topology recorded in CANONICAL_INDEX.json; `install-links.ps1` is idempotent |
| CloudTech xml rename breaks WinSW | medium | Phase M5 includes dry-run install.cmd verification |
