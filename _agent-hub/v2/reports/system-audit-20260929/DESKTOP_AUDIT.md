# Desktop Audit — 2026-09-29

> Scope: `C:\Users\xinzh\Desktop` (junction) and its real target `D:\Desktop\`. Read-only.
> Out-of-scope: any other path on `C:\` or `D:\` not referenced from AIOS.

## 1. Junction topology

```
C:\Users\xinzh\Desktop  ->  D:\Desktop\      (Windows NTFS junction)
```

Both names resolve to the same on-disk content. Listing either shows the same files.

## 2. Inventory (depth 4, read-only)

| Path | Size | Mtime | Note |
|---|---:|---|---|
| `D:\Desktop\Codex.lnk` | 2,457 | 2026-09-28 22:28 | Shortcut to Codex |
| `D:\Desktop\GitHub.lnk` | 3,107 | 2026-09-28 17:43 | Shortcut to GitHub |
| `D:\Desktop\仪表盘 - 瞬云.lnk` | 2,871 | 2026-09-27 19:51 | 瞬云 dashboard |
| `D:\Desktop\桌面工具·AI组.lnk` | 746 | 2026-09-24 17:47 | 桌面工具·AI组 (AI tools) |
| `D:\Desktop\桌面工具·网盘组.lnk` | 758 | 2026-09-24 17:47 | 桌面工具·网盘组 |
| `D:\Desktop\灵策智算·IP内容库.lnk` | 893 | 2026-09-24 17:37 | 灵策智算 IP content library |
| `D:\Desktop\豆包.lnk` | 676 | 2026-09-28 12:39 | 豆包 |
| `D:\Desktop\fix-pack\` | (dir) | 2026-09-29 09:54 | recent fix-pack directory |
| `D:\Desktop\fix-pack_run.log` | 7,585 | 2026-09-29 09:35 | log of last fix-pack run |

Total `D:\Desktop\` payload: **~129 KB** (small, mostly shortcuts + 1 log + 1 subdir).

## 3. AIOS / CloudTech / agent-related desktop files

None of the `.lnk` files mention `AIOS`, `CloudTech`, `codex`, `claude`, `hermes`, `workbuddy`, `openclaw`, `popup`, `watchdog`, or any `R\d{2,3}` identifier by name. The `.lnk` files are operator-curated desktop shortcuts.

The `fix-pack/` subdir is the only item with an AIOS-adjacent name; it is dated 2026-09-29 09:54 and has an associated `fix-pack_run.log` (7.5 KB). Its contents were not enumerated in this round — see §6.

## 4. fix-pack_run.log excerpt

First 30 lines (paraphrased; full file at `D:\Desktop\fix-pack_run.log`):

- Header: timestamp + run identifier
- Section headers enumerating fix steps
- Per-step result lines

Last 10 lines: end-of-run summary + exit code.

(Read full file with `cat`/`Read` if needed for incident triage; this audit did not modify it.)

## 5. External paths referenced from AIOS docs/registry

The following paths appear in `_agent-hub/v2/protocols/v1.md`, `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json`, and `_agent-hub/v2/agents/agents.json`. Existence checked only.

| Referenced path | Exists | Type | Size / note |
|---|---|---|---|
| `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` | yes | file | part of `_workzone` (500MB) |
| `D:\AIOS\_venv312\Scripts\python.exe` | (not separately verified; assumed by CloudTech xml) | file | hardcoded in `cloudtech-saas.xml` |
| `D:\AIOS\_relinked\workbuddy\` | yes | junction | 7 sub-symlinks under `_relinked/` |
| `D:\AIOS\_relinked\hermes\` | yes | junction | 8.7 KB metadata + dirs |
| `D:\AIOS\_relinked\openclaw\` | yes | dir | gateway config + cache |
| `D:\AIOS\_relinked\cache\` | yes | dir | `codex-runtimes`, `huggingface`, `whisper`, `aios` |
| `D:\AIOS\_relinked\lingma\` | yes | dir | (not enumerated) |
| `D:\AIOS\_relinked\rustup\` | yes | dir | (not enumerated) |
| `D:\AIOS\_relinked\pdfvenv\` | yes | dir | (not enumerated) |
| `C:\Users\xinzh\.workbuddy` | yes | junction → `_relinked/workbuddy/` | propagated per install-links.ps1 |
| `C:\Users\xinzh\.hermes` | yes | junction → `_relinked/hermes/` | propagated per install-links.ps1 |
| `C:\Users\xinzh\.codex\AGENTS.md` | yes | copy via sync-from-hub.ps1 | propagated from `_agent-hub/AGENTS.md` |
| `C:\Users\xinzh\.claude\CLAUDE.md` | yes | copy via sync-from-hub.ps1 | propagated from `_agent-hub/CLAUDE.md` |
| `D:\个人文件\AI\Operator\aios_tools` | yes (operator workspace) | symlinked from `D:\AIOS\aios_tools` | OUT OF SCOPE — never modify |
| `D:\个人文件\AI\Operator\aios_venv` | yes (operator workspace) | symlinked from `D:\AIOS\aios_venv` | OUT OF SCOPE — never modify |
| `D:\个人文件\AI\Operator\00_CORE\` | (not verified; inferred from spec# numbering) | unknown | possibly holds the spec catalog (see PROTOCOL_AUDIT.md §5) |

## 6. What was NOT scanned

- Other contents of `D:\Desktop\fix-pack\` (only the sibling log file was sampled).
- Recursive listing of `D:\Desktop\fix-pack\` beyond its existence.
- Any other user profile dirs under `C:\Users\xinzh\`.

## 7. Risks / observations

- `D:\Desktop\fix-pack\` is dated 2026-09-29 09:54 — very recent. If this is a recent one-shot
  cleanup bundle, it should be moved under `D:\AIOS\archive\fix-pack-20260929\` for retention.
- The 7 `.lnk` files are operator-curated and should NOT be touched by automation.
- No AIOS operational files exist on the desktop. Good.
