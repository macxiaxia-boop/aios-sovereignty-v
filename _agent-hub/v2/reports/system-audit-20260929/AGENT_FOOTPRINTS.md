# Agent Footprints Audit — 2026-09-29

> Scope: AI agent home/config directories on Windows. Read-only metadata only.
> Secrets/tokens are NEVER reported (path + size + mtime + description only).

## 1. Junction topology

```
C:\Users\xinzh\.workbuddy  ->  D:\AIOS\_relinked\workbuddy\    (junction)
C:\Users\xinzh\.hermes     ->  D:\AIOS\_relinked\hermes\        (junction)
C:\Users\xinzh\.codex      (no junction; populated by sync-from-hub.ps1)
C:\Users\xinzh\.claude     (no junction; populated by sync-from-hub.ps1)
```

The hub cross-agent identity (`_agent-hub/AGENTS.md`, `_agent-hub/CLAUDE.md`,
`_agent-hub/MEMORY.md`, `_agent-hub/SOUL.md`, `_agent-hub/USER.md`,
`_agent-hub/BOOTSTRAP.md`, `_agent-hub/IDENTITY.md`) propagates to the agent
homes via two mechanisms:

1. **Junction** (real-time): workbuddy + hermes identity files are NTFS junctions
   back into `D:\AIOS\_relinked\…`. Edits to the hub are visible immediately.
2. **Copy sync** (eventual): codex + claudecode are populated by
   `D:\AIOS\_agent-hub\sync-from-hub.ps1` after each hub edit.

## 2. Per-agent home — key files only

### 2.1 `C:\Users\xinzh\.codex\`

| File | Size | Mtime | Note |
|---|---:|---|---|
| `.codex-global-state.json` | 62,902 | 2026-09-29 13:32 | Codex runtime state (NOT a secret) |
| `.codex-global-state.json.bak` | 62,902 | 2026-09-29 13:32 | identical copy (rolled) |
| `AGENTS.md` | 2,052 | 2026-09-28 18:53 | junctioned/copied from `_agent-hub/AGENTS.md` |
| `AGENTS.md.bak` | 18,771 | 2026-09-27 19:47 | superseded by AGENTS.md |
| `_archived_R244_AGENTS_v109_20260927/` | (dir) | 2026-09-27 19:46 | archived v109 of AGENTS.md |
| `_archived_R93/` | (dir) | 2026-09-19 19:43 | archived R93 |
| `_archived_v13_pre_20260924/` | (dir) | 2026-09-24 18:05 | archived v13 pre-2026-09-24 |
| `.sandbox/`, `.sandbox-bin/`, `.sandbox-secrets/`, `.chatgpt-projects/`, `.tmp/` | (dirs) | various | sandbox scratch — listed but not enumerated |

Secrets explicitly NOT reported: `secrets/*`, `.sandbox-secrets/*`, any token/key file.

### 2.2 `C:\Users\xinzh\.claude\`

| File | Size | Mtime | Note |
|---|---:|---|---|
| `.mcp.json` | 2,742 | 2026-09-12 20:20 | MCP config (aios-interop + playwright) — DO NOT TOUCH |
| `.mcp-secrets.json.2026-09-05.json` | 220 | 2026-09-05 11:53 | secret-bearing file — name/size only |
| `.minimax-api-key` | 125 | 2026-09-03 15:43 | secret-bearing file — name/size only |
| `CLAUDE.md` | 1,731 | 2026-09-28 18:53 | junctioned/copied from `_agent-hub/CLAUDE.md` |
| `CLAUDE.md.bak` | 11,496 | 2026-09-28 12:39 | superseded |
| `AGENTS.md` | 2,052 | 2026-09-28 18:53 | (in this folder too) |
| `BEHAVIORAL-DELTA.md` | 12,047 | 2026-08-23 17:09 | delta notes |
| `CLAUDE-keywords.md` | 19,174 | 2026-09-24 11:42 | keyword reference |
| `agents/` | (dir) | 2026-09-05 11:54 | per-agent subdir |
| `backups/`, `_backups/`, `_archive-sessions/`, `_scripts/` | (dirs) | various | enumerated but not deep-scanned |
| `cache/`, `cc-switch/`, `daemon/`, `debug/`, `embedding/` | (dirs) | various | cache + tooling |
| `feedback-R193-*.md` | 6,375–8,743 | 2026-09-26 12:02–12:38 | feedback trail |
| `_tmp_r490.md` | 30,175 | 2026-09-26 12:02 | scratch |

### 2.3 `C:\Users\xinzh\.workbuddy` → `D:\AIOS\_relinked\workbuddy\`

| File | Size | Mtime | Note |
|---|---:|---|---|
| `.skill-list-cache.json` | 33,021 | 2026-09-29 12:33 | skill index cache |
| `.connectors-marketplace.meta.json` | 247 | 2026-09-28 18:44 | marketplace meta |
| `.legacy-localstorage-migration.done` | 79 | 2026-09-29 11:58 | migration marker |
| `.workbuddy-sqlite-migrations/` | (dir) | 2026-09-29 09:04 | SQLite migrations |
| `45e357fa-c2ec-4bd0-b734-9b016a2759d7/` | (dir) | 2026-09-29 09:04 | session dir |
| `AGENTS.md` | 2,052 | 2026-09-28 18:53 | junctioned |
| `BOOTSTRAP.md` | 1,089 | 2026-09-29 09:04 | bootstrap (not in hub) |
| `CLAUDE.md` | 1,731 | 2026-09-28 18:53 | junctioned |
| `IDENTITY.md` | 2,745 | 2026-09-28 18:53 | junctioned |
| `IDENTITY.md.bak` | 582 | 2026-09-22 16:30 | superseded |
| `MEMORY.md` | 4,827 | 2026-09-29 12:30 | junctioned |
| `MEMORY.md.bak` | — | — | junction → `D:\AIOS\_agent-hub\MEMORY.md` |
| `SOUL.md` | 2,745 | 2026-09-28 18:53 | junctioned |
| `SOUL.md.bak` | 1,792 | 2026-09-22 16:30 | superseded |
| `USER.md` | 1,901 | 2026-09-28 18:53 | junctioned |
| `USER.md.bak` | 536 | 2026-09-22 16:30 | superseded |
| `app/`, `artifact-index/`, `audit-log/`, `binaries/`, `cache/`, `changes-detail/`, `changes-index/`, `connectors/` | (dirs) | various | workbuddy core |

### 2.4 `C:\Users\xinzh\.hermes` → `D:\AIOS\_relinked\hermes\`

| File | Size | Mtime | Note |
|---|---:|---|---|
| `.skills_prompt_snapshot.json` | 44,840 | 2026-09-27 14:43 | skills prompt snapshot |
| `SOUL.md` | 8,922 | 2026-09-16 16:58 | Hermes-specific SOUL |
| `SOUL.md.bak-2026-09-13-pre-ssot-injection` | 4,407 | 2026-09-13 14:45 | pre-SSOT backup |
| `.env`, `auth.json` | small | recent | secrets — name/size only, NOT content |
| `.hermes_history` | 890 | 2026-09-16 13:17 | history log |
| `.backup.lock` | 1 | 2026-09-26 21:36 | lock file |
| `audio_cache/`, `backups/`, `bin/`, `cache/`, `channel_directory.json` | mixed | recent | Hermes core |
| `_backup-20260819-config-cleanup/`, `.curator_backups/` | (dirs) | 2026-08-19 / 2026-09-15 | historical backups |

## 3. AIOS references inside agent homes

Files in agent homes whose name contains "AIOS" or referenced AIOS paths:

- `C:\Users\xinzh\.claude\AGENTS.md` — references AIOS hub
- `C:\Users\xinzh\.claude\CLAUDE.md` — references AIOS hub
- `C:\Users\xinzh\.claude\CLAUDE-keywords.md` — keyword reference (19 KB)
- `C:\Users\xinzh\.claude\BEHAVIORAL-DELTA.md` — delta notes (12 KB)
- `C:\Users\xinzh\.codex\AGENTS.md` — references AIOS hub
- `D:\AIOS\_relinked\workbuddy\AGENTS.md` — junctioned AIOS shared file
- `D:\AIOS\_relinked\hermes\SOUL.md` — Hermes-specific SOUL with AIOS context

## 4. Risks

1. **Stale .bak files in agent homes**: `CLAUDE.md.bak` (11.5 KB), `IDENTITY.md.bak` (582 B),
   `SOUL.md.bak` (1.8 KB), `USER.md.bak` (536 B), `AGENTS.md.bak` (18.8 KB), `MEMORY.md.bak`
   (junction) — all superseded by current hub files. Listed in `CLEANUP_CANDIDATES.json`.
2. **agent homes are NOT scanned for content**. Only metadata + filename keywords. Any secrets
   are present but not enumerated.
3. **`C:\Users\xinzh\.workbuddy\MEMORY.md` is itself a junction to hub MEMORY.md** — this is
   intentional and not a duplicate.
4. **Cross-agent identity files have **multiple** copies** (workbuddy + hub + maybe codex/claude
   copies). Current-pointer rules in PROTOCOL_AUDIT.md §2 ensure exactly one is `current`.
5. **Symlinks under `_relinked/`** (cache, hermes, lingma, openclaw, pdfvenv, rustup, workbuddy)
   are directory junctions / NTFS junctions. Their targets are read but never followed
   automatically by governance tools (see `scan_inventory.py` reparse guard).
