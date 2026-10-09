# Cross-Agent Shared Memory Hub

> **One edit in `D:\AIOS\_agent-hub\` + one sync run = all agents see it.**

---

## What's Here

```
D:\AIOS\_agent-hub\
├── SOUL.md                Cross-agent identity (workbuddy + claudecode + codex read)
├── USER.md                Cross-agent user profile
├── AGENTS.md              Shared instructions (codex reads)
├── CLAUDE.md              Shared instructions (claudecode reads)
├── MEMORY.md              Cross-agent long-term memory (workbuddy reads)
├── memory/                Cross-agent daily logs
├── sync-from-hub.ps1      Copy hub content to each agent's config dir (PRIMARY)
├── install-links.ps1      Try real NTFS junctions (advanced - needs admin/dev mode)
└── README.md              This file
```

## Current State (2026-09-28)

**Sync mode (copy) is active**. After running `sync-from-hub.ps1`, all agents have a copy of the hub content. To re-sync after editing, run the script again.

| File in agent dir | Source in hub | Sync status |
|---|---|---|
| `C:\Users\xinzh\.workbuddy\SOUL.md` | `D:\AIOS\_agent-hub\SOUL.md` | ✓ Synced |
| `C:\Users\xinzh\.workbuddy\USER.md` | `D:\AIOS\_agent-hub\USER.md` | ✓ Synced |
| `C:\Users\xinzh\.workbuddy\MEMORY.md` | `D:\AIOS\_agent-hub\MEMORY.md` | ✓ Synced |
| `C:\Users\xinzh\.workbuddy\IDENTITY.md` | `D:\AIOS\_agent-hub\SOUL.md` | ✓ Synced |
| `C:\Users\xinzh\.codex\AGENTS.md` | `D:\AIOS\_agent-hub\AGENTS.md` | ✓ Synced |
| `C:\Users\xinzh\.claude\CLAUDE.md` | `D:\AIOS\_agent-hub\CLAUDE.md` | ✓ Synced |
| `C:\Users\xinzh\.workbuddy\memory\` | `D:\AIOS\_agent-hub\memory\` | ✓ Mirrored |

## Workflow (the loop)

1. **Edit** any file in `D:\AIOS\_agent-hub\` (e.g. `AGENTS.md`)
2. **Run** `D:\AIOS\_agent-hub\sync-from-hub.ps1`
3. **All agents** see the change on next session

```powershell
# After editing hub:
powershell -ExecutionPolicy Bypass -NoProfile -File D:\AIOS\_agent-hub\sync-from-hub.ps1
```

## Why Copy Mode (Not Junctions)?

I tried `install-links.ps1` first to create real NTFS junctions (one-file-edit-multiple-agents-see). It failed because:
- `New-Item -ItemType Junction` (PowerShell 5.1) only supports **directory** junctions, not file junctions
- File symlinks need admin or Windows Developer Mode
- The sandbox blocked `cmd.exe /c mklink` and `wsl.exe`

So I fell back to copy mode. **Trade-off**: requires manual `sync-from-hub.ps1` run after edits. **Benefit**: works in any environment.

If you have admin / dev mode, you can run `install-links.ps1` to upgrade to real junctions (one-time). Until then, sync mode works.

## Sync Mode Limitations

1. **No live sync** — must run script after editing
2. **No bidirectional** — edits in agent dirs won't propagate to hub
3. **Stale data risk** — if you forget to sync, agents see old content

For a single-user dev workflow this is fine. For multi-user, set up a real shared drive (OneDrive/Dropbox) or use `install-links.ps1` with admin.

## What I Did NOT Touch

- `C:\Users\xinzh\.codex\config.toml` (your MCP config)
- `C:\Users\xinzh\.claude.json` (claudecode's MCP config with aios-interop + playwright)
- `D:\个人文件\AI\Operator\aios_tools\` (your aios toolchain)
- `D:\AIOS\_relinked\hermes\hermes-agent\` (Hermes source)
- `C:\Users\xinzh\WorkBuddy\2026-09-28-17-53-41\.workbuddy\root-cause-fix\` (channel fix artifacts)

## Open Items

- **Hermes integration**: see "Hermes" section below
- **OpenClaw integration**: user needs to provide path (not found in my search)

## Manual: Hermes Integration

Hermes uses its own memory system (FTS5 + Honcho). Options to connect:

### Option A: Symlink in Hermes's memory dir (Linux side)

```bash
# In WSL2
mkdir -p ~/.hermes/external
ln -s /mnt/d/AIOS/_agent-hub/MEMORY.md ~/.hermes/external/MEMORY.md
```

Then in `~/.hermes/config.yaml`:
```yaml
memory:
  provider: honcho
  external_paths:
    - /mnt/d/AIOS/_agent-hub/memory
```

### Option B: Use a Hermes memory provider plugin

See `hermes-agent/plugins/memory/` for plugin list. Write a custom plugin that reads from `D:\AIOS\_agent-hub\`.

**Note**: I did NOT auto-modify Hermes. Its memory architecture is complex and risky to change without user confirmation.

## Manual: OpenClaw Integration

**OpenClaw location unknown** — I searched `C:\Users\`, `D:\AIOS\`, WSL2 `/root/` and found nothing.

**Action needed from user**: tell me where OpenClaw is installed (path to its config dir), then I'll add it to the sync map.

## What Each Agent Reads (After Sync)

| Agent | At session start reads |
|---|---|
| workbuddy | `~/.workbuddy/SOUL.md` + `USER.md` + `MEMORY.md` + `IDENTITY.md` + `memory/YYYY-MM-DD.md` |
| codex | `~/.codex/AGENTS.md` |
| claudecode | `~/.claude/CLAUDE.md` |
| Hermes | `~/.hermes/config.yaml` + Honcho state (its own system, NOT modified) |
| OpenClaw | TBD |

After `sync-from-hub.ps1` runs, the first 3 read from the same content. Hermes keeps its own.

## Backup

When `sync-from-hub.ps1` runs, it backs up existing files to `<name>.bak`. To roll back:
```powershell
# Example: roll back AGENTS.md
del C:\Users\xinzh\.codex\AGENTS.md
ren C:\Users\xinzh\.codex\AGENTS.md.bak C:\Users\xinzh\.codex\AGENTS.md
```

## Files in This Directory

- `SOUL.md`, `USER.md`, `AGENTS.md`, `CLAUDE.md`, `MEMORY.md` — canonical content
- `memory/` — daily logs (YYYY-MM-DD.md)
- `sync-from-hub.ps1` — main script (use this)
- `install-links.ps1` — advanced (needs admin)
- `README.md` — this file
- `*.log`, `*.txt` (debug/sync logs) — safe to delete
- `v2/` — AIOS Hub v2 (R320 · 2026-09-29). Bidirectional, versioned, machine-validated. See `v2/README.md`.

---

## v2 (R320 · R320.1 · 2026-09-29)

`v2/` is the **additive, versioned, machine-validated** extension of this hub. It addresses the
three v1 limitations explicitly:

| v1 limitation | v2 answer |
|---|---|
| No live sync | File queue with `enqueue / claim / ack / deadletter` |
| No bidirectional | Bidirectional envelopes with `correlation_id` + reply types |
| Stale data risk | JSON Schema validation + idempotency_key dedup + event log |

**Scope** (see `v2/README.md`):

- 5 agents registered: `claudecode` / `codex` / `workbuddy` / `hermes` / `openclaw`
- 7 message types: `message` / `task` / `status` / `result` / `ack` / `heartbeat` / `error`
- Task state machine: `queued → running → succeeded / failed (→ retry → queued)`, with heartbeat/timeout/retry
- CLI: `python D:\AIOS\_agent-hub\v2\cli\aiosv2.py {init,status,health,send,receive,ack,submit-task,update-task,watch,tick}`
- Tests: `python D:\AIOS\_agent-hub\v2\tests\run_all_tests.py` (8 modules, 42 cases)
- Reports: `D:\AIOS\_agent-hub\v2\reports\IMPLEMENTATION_REPORT.md`, `health.json`, `status.json`, `test_run.json`, `test-output.txt`

**R320.1 honest state** (Codex independent audit applied):

- **NOT** 11/11; see `v2/reports/IMPLEMENTATION_REPORT.md` §1 for the factual table.
- Test suite source code is **complete and ready to execute**, but live execution in this
  CC session is **BLOCKED** by the Bash sandbox (denies `python <script>`); the source
  was statically audited and the driver writes `reports/test-output.txt` + `reports/test_run.json`
  on first run. **Codex is asked to re-run** from a permitted shell.
- `br-claudecode-openclaw`: was set to `built/partial` in R320 — that was wrong. R320.1
  rolled it back to `loopback_only / unverified` (no real two-runtime round-trip was proven).

**v2 does NOT modify v1**: this README, the 5 markdown files, `sync-from-hub.ps1`, and `install-links.ps1`
are unchanged. v2 sits alongside them. Rollback = `Remove-Item -Recurse -Force D:\AIOS\_agent-hub\v2`.

---

_Maintained by workbuddy + v2 by Claude Code under Codex supervision. Last updated: 2026-09-29 (R320.1)._
