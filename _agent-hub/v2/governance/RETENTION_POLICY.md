# RETENTION POLICY — D:\AIOS

> Status: **proposed 2026-09-29** (R281 governance wave).
> This is a **policy document**, not an action. No file is deleted/moved by this round.

## 1. Principles

1. **Real source > training-data guess** — never claim a file is duplicate/superseded without sha256 or registry pointer evidence.
2. **One current, many archives** — exactly one `current` file per concept; everything else moves to `archive/<R-id>/` with index.
3. **Logs rotate, never delete in-place** — log retention uses size or age; deletion is automatic and bounded.
4. **Build artifacts evict by LRU** — anything under `artifacts/` older than retention may be evicted; before eviction, an index entry is written.
5. **Never auto-evict registries / shared identity / protocols / schemas** — those are protected types.

## 2. Retention windows (proposed, pending user approval)

| Category | Path pattern | Retention | Auto-action |
|---|---|---|---|
| Shared identity | `_agent-hub/{AGENTS,CLAUDE,MEMORY,SOUL,USER,BOOTSTRAP,IDENTITY}.md` | forever | none |
| Protocol / schema / registry | `_agent-hub/v2/protocols/`, `_agent-hub/v2/schemas/`, `AIOS_RECONSTRUCTION/{01_REGISTRY,02_CANONICAL,03_BRIDGES,04_CAPABILITY_GRAPH,08_RADAR}/` | forever | none |
| Logs | `*.log` anywhere under `D:\AIOS\` (excluding `_relinked/openclaw/logs/`, `_relinked/workbuddy/`, `_relinked/hermes/` which are agent-owned) | 30 days OR 50MB | rotate (rename `.log` → `.log.1`, keep last 5) |
| Audit reports | `_agent-hub/v2/reports/system-audit-*/AUDIT_MANIFEST.json` | forever | none |
| Run records | `_agent-hub/v2/runs/<run-id>/` | 90 days | compress to `archive/runs/<year>/<run-id>.tar.zst` |
| Task records | `_agent-hub/v2/tasks/<task-id>.json` | 90 days after `terminal_state` | compress to `archive/tasks/` |
| Idempotency index | `_agent-hub/v2/state/idempotency_index.json` | forever (small) | compact when > 10K entries |
| Build artifacts | `D:\AIOS\_out\`, `D:\AIOS\artifacts\`, `D:\AIOS\_patches\` | 90 days for raw outputs | archive under `artifacts/_archive/<date>/` |
| Backups | `D:\AIOS\_backups\`, `D:\AIOS\_backup_aios_exe_*`, `D:\AIOS\_r274_install_backup` | 30 days | manual review; not auto-deleted |
| Cached dedup workspaces | `D:\AIOS\_dr_v3.0_uncompressed_workspace\`, `D:\AIOS\_e_drive_dedup_workspace\` | 7 days | warning; not auto-deleted |
| Legacy `_archived_*` snapshots | `D:\AIOS\_archived_*/` | 180 days | compress to `archive/legacy/<date>.tar.zst` |

## 3. NEVER auto-delete (protected)

- Anything under `D:\个人文件\AI\Operator\` (operator workspace; AIOS symlinks point there but AIOS does not own them)
- Anything in `C:\Users\xinzh\.codex\`, `C:\Users\xinzh\.claude\`, `C:\Users\xinzh\.workbuddy\`, `C:\Users\xinzh\.hermes\` (junctioned/synced; agent-owned)
- `.git/` (version control)
- `.mcp-secrets.json`, `*.token`, `*.key`, `.env` (secrets) — read-only metadata only
- Watchdog/daemon PID files, lock files (live state)
- `_audit_all_report.txt` and similar governance audit trails

## 4. Storage capacity thresholds (C:/D:)

| Volume | Warning threshold | Critical threshold |
|---|---|---|
| `D:\` total | 80% | 90% |
| `D:\AIOS` total | 5 GB | 10 GB |
| `D:\AIOS\_workzone` | 600 MB | 1 GB |
| `D:\AIOS\_capability` (registry backups) | 200 MB | 500 MB |
| `D:\AIOS\_backups` | 100 MB | 500 MB |
| `D:\AIOS\daemons_v2` (logs) | 200 MB | 500 MB |

When critical is hit, housekeeper emits a `quarantine/` move recommendation (not an auto-delete).

## 5. Cleanup approval workflow

```
[housekeeper.py --dry-run]
  -> produces governance/CLEANUP_CANDIDATES.json + reports/.../CLEANUP_REPORT.md
  -> user reviews
  -> user approves per-row OR by category
  -> user runs housekeeper.py --apply --approved-by USER --rows path1 path2 ...
  -> housekeeper moves files to archive/ or quarantine/ (NEVER deletes in-place)
  -> indexes the move in governance/MOVE_LOG.json
```

This round (R281 audit) ships **only** the dry-run path. The `--apply` path is a
separate round and requires its own user approval.

## 6. Legacy zones (do NOT add new files)

- `D:\AIOS\aios_tasks\` — R186..R215 task workspace
- `D:\AIOS\daemons_v2\` — v2 daemons (log-heavy)
- `D:\AIOS\_scripts\` and `D:\AIOS\_scripts_tmp\` — ad-hoc scripts
- `D:\AIOS\_tools\` — ad-hoc tools
- `D:\AIOS\_out\` — build outputs
- `D:\AIOS\_patches\` — patches to other projects
- `D:\AIOS\_archived_*/` — explicit archive snapshots

These remain valid homes for files already there; new work that doesn't fit goes to
`D:\AIOS\agents/`, `D:\AIOS\protocols/`, `D:\AIOS\projects/`, `D:\AIOS\artifacts/`,
`D:\AIOS\logs/`, `D:\AIOS\runs/`, `D:\AIOS\reports/`, `D:\AIOS\archive/`, or
`D:\AIOS\governance/`.

## 7. Audit log of changes

Every future housekeeping action MUST be appended to:
`D:\AIOS\_agent-hub\v2\governance\MOVE_LOG.json` (created on first apply).
This file is append-only and rotated annually.
