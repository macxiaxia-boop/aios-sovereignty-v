# PLACEMENT RULES — D:\AIOS file placement standard

> Status: **R281.2 — 2026-09-29** (R281 governance wave, second pass).
> Read by every AI that drops files into this workspace. Supersedes the
> de-facto "anywhere in D:\AIOS" practice. Backwards-compatible: existing
> user files are NOT relocated in this round. Only newly-created governance
> test/aux assets were reorganized under `governance/tools/` and
> `governance/tests/fixtures/`.

## 1. Top-level canonical layout

New files MUST land under one of these top-level subdirs:

| Path | Owner | Purpose | Examples |
|---|---|---|---|
| `agents/{codex,claudecode,workbuddy,hermes,openclaw}/` | each agent's own identity, scripts, ephemeral state | per-agent working files | `agents/codex/_local_cache.md` |
| `protocols/` | multi-agent shared wire format / SSOT specs | `protocols/v1.md`, schemas | (see `CANONICAL_INDEX.json`) |
| `projects/<name>/` | a single project workspace | `projects/cloudtech/`, `projects/swarmclaw/` |
| `artifacts/` | build outputs, screenshots, binaries | `artifacts/R222/sc001.png` |
| `logs/` | all rolling logs (rotated) | `logs/aios_daemon.log` |
| `runs/` | one record per execution attempt | `runs/<run-id>/attempt-N.json` |
| `reports/` | analytical reports (markdown + json) | `reports/system-audit-20260929/` |
| `archive/` | read-only historical content with manifest | `archive/R212/AIOS_RECONSTRUCTION_PROGRESS.json` |
| `quarantine/` | files removed from active placement pending decision | `quarantine/_admin_check_svc_v2.py.20260929.md` |
| `governance/` | this directory: registry + policy + scripts | `governance/PROTOCOL_REGISTRY.json` |

Subdirs `aios_tasks/`, `daemons_v2/`, `tools/`, `_capability/`, `_scripts/`, `_tools/`,
`_workzone/`, `_out/`, `_patches/`, `_backups/`, `_dr_v3.0_uncompressed_workspace/`,
`_e_drive_dedup_workspace/`, `_r274_install_backup/`, `wmic_forensics/`,
`_archived_*/` are **legacy paths** — keep adding to them only if your work is
already inside that subdir's scope. New work that doesn't fit MUST go to the
canonical layout above.

## 2. Naming

| Rule | Reason |
|---|---|
| Prefix operational scripts with `_<scope>_` (underscore) | keep them sorted below real artifacts |
| Tag with R-number when tied to a remediation: `R267_idempotency_fix.py` | trace to governance event |
| Use lowercase snake_case for Python, kebab-case for shell, PascalCase only for classes | conventional |
| Date suffix `_YYYYMMDD` only on time-sensitive artifacts | sortable |
| `.bak`, `.disabled`, `.disabled_real`, `.DISABLED`, `.bak_pre_v2`, `.bak_v2_failed`, `.bak_C_*` are **migration-time only**. New code MUST NOT introduce these. | they're noise |

## 3. Compatibility / migration plan

This round is **non-destructive** — no existing file is moved. Future migrations:

| Phase | Trigger | Action |
|---|---|---|
| M1 | This audit accepted by user | Record legacy paths in `RETENTION_POLICY.md` "legacy zones" |
| M2 | `governance/housekeeper.py --apply` enabled (separate round, explicit user approval) | Move files into canonical layout per rules in section 1 |
| M3 | `archive/` reorganized | Compress and index `_archived_*/` into `archive/<R-id>/` |

## 4. Forbidden placement

- Desktop (`C:\Users\xinzh\Desktop` is junctioned to `D:\Desktop`): never place operational files there. Use `D:\AIOS\artifacts/` instead.
- `D:\` root or `D:\AIOS\` root: never write loose files at top; only first-party dirs go there.
- Windows TEMP (`%TEMP%`): never as a final location; only as scratch (auto-cleared).
- `_agent-hub/` (legacy) or `_agent-hub/v1/`: read-only; new shared content goes to `_agent-hub/v2/`.

## 5. Single source of truth rule

Every machine-readable identity / spec / wire format must have exactly one canonical file. The
canonical pointer is determined by (in order):

1. `governance/PROTOCOL_REGISTRY.json` field `current_id` for that protocol
2. `governance/CANONICAL_INDEX.json` mapping
3. Explicit `supersedes` chain in the file's own frontmatter
4. Hash + mtime as evidence only — never as the sole selector

If two files claim to be current, the conflict is logged in `PROTOCOL_AUDIT.md` and the
registry status for both flips to `unknown` until user decides.

### 5a. Canonical registry surface (R281.2)

**The ONLY canonical protocol registry is `governance/PROTOCOL_REGISTRY.json`.**

Files under the following subdirectories are NOT canonical and MUST NOT be read
to resolve a `current_by_family` pointer:

- `governance/tools/` — maintenance utilities (`compute_protocol_hashes.py`,
  `build_protocol_registry.py`, etc.). These are operator-facing scripts, not
  data.
- `governance/tests/fixtures/` — test isolation fixtures. Anything prefixed
  `TEST_ONLY_` here is a fixture by definition and is exempt from canonical
  resolution.

`protocol_registry.py validate` and `list-current` operate ONLY on the
canonical registry. Test fixtures are only consulted when the caller
explicitly passes `--registry <fixture_path>` for test isolation.

The canonical file itself MUST NOT reference a `current` entry whose `path`
points into `governance/tools/` or `governance/tests/`; the validator will
flag such entries.

## 6. Agent homes

| Agent home | Linked from | Authority |
|---|---|---|
| `C:\Users\xinzh\.claude\` | symlink target not used; copy via `sync-from-hub.ps1` | CC reads `~/.claude/CLAUDE.md` |
| `C:\Users\xinzh\.codex\` | symlink target not used; copy via `sync-from-hub.ps1` | Codex reads `~/.codex/AGENTS.md` |
| `C:\Users\xinzh\.workbuddy\` | junction to `D:\AIOS\_relinked\workbuddy` | WB reads junctioned files |
| `C:\Users\xinzh\.hermes\` | junction to `D:\AIOS\_relinked\hermes` | Hermes reads junctioned files |

All cross-agent shared identity (`AGENTS.md`, `CLAUDE.md`, `MEMORY.md`, `SOUL.md`, `USER.md`,
`BOOTSTRAP.md`, `IDENTITY.md`) lives in `D:\AIOS\_agent-hub\` and propagates via the
junction network + `sync-from-hub.ps1` fallback.

## 7. What this rule does NOT do

- It does NOT delete, move, or rename any existing file in this round.
- It does NOT auto-clean duplicate or bak files (those are listed in
  `governance/CLEANUP_CANDIDATES.json` for explicit user review).
- It does NOT touch `D:\个人文件\AI\Operator\` (operator workspace, out of scope).
