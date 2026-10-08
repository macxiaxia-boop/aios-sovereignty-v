# AIOS Inventory Summary — 2026-09-29 (R281.2)


> **R281.2 supersedes R281.1 numbers.** R281.1 over-excluded the entire `_agent-hub/v2/reports` subtree, hiding the formal reports (IMPLEMENTATION_REPORT.md, health.json, status.json, test_run.json, test-output.txt) from inventory. R281.2 narrows scanner self-exclusion to EXACTLY TWO roots: `_agent-hub/v2/governance` (this round's governance tools + assets) and `_agent-hub/v2/reports/system-audit-20260929` (this round's self-growing output dir). The rest of `v2/reports/` is scanned normally. CSV ↔ manifest consistency verified (files/dirs/bytes exactly match).

Captured: 2026-09-29T16:54:20Z

Scope: `D:\AIOS` (read-only metadata scan, no content beyond hash for ≤20MB hashable files).

Self-excluded roots (scanner's own outputs, exactly TWO): `governance/`, `reports/system-audit-20260929/`.


## Headline numbers

- **Total rows scanned**: 71,799
- **Files**: 71,072
- **Dirs**: 727
- **Symlinks**: 0
- **Junctions (Windows reparse)**: 0
- **Total payload bytes** (sum of file size_bytes): 2,575,975,014 (~2456.6 MB)
- **Duplicate sha256 groups (≥2 entries)**: 631
- **Bak/disabled suffix files**: 161
- **Files ≥5MB**: 98

## Size distribution (files)

| bucket | count |
|---|---|
| <1KB | 49,766 |
| 1KB-100KB | 20,315 |
| 100KB-1MB | 800 |
| 1MB-10MB | 138 |
| 10MB-100MB | 53 |
| >100MB | 0 |

## Top extensions

| ext | count |
|---|---|
| .go | 17,132 |
| .md | 7,616 |
| .js | 5,998 |
| .(no_ext) | 5,605 |
| .ts | 4,698 |
| .json | 4,469 |
| .txt | 4,446 |
| .py | 3,137 |
| .map | 2,586 |
| .log | 1,581 |
| .ps1 | 1,192 |
| .cjs | 1,132 |
| .s | 980 |
| .png | 708 |
| .cmd | 640 |
| .mjs | 566 |
| .pyc | 519 |
| .psm1 | 515 |
| .tmp | 468 |
| .crt | 406 |

## Top 20 storage hotspots (top-level dirs)

| top | files | dirs | bytes | MB |
|---|---:|---:|---:|---:|
| `_relinked` | 54,548 | 100 | 1,378,901,207 | 1315.0 |
| `.git` | 5,612 | 268 | 369,823,278 | 352.7 |
| `_workzone` | 1,561 | 55 | 356,763,355 | 340.2 |
| `daemons_v2` | 175 | 13 | 168,036,906 | 160.3 |
| `_archived_2026-09-18` | 20 | 3 | 136,643,294 | 130.3 |
| `_capability` | 5,331 | 25 | 82,121,801 | 78.3 |
| `_backup_aios_exe_周二022609_093048` | 4 | 1 | 37,151,064 | 35.4 |
| `_archived_20260925_P0` | 93 | 14 | 19,238,025 | 18.3 |
| `_backups` | 3,168 | 175 | 15,106,892 | 14.4 |
| `_desktop_screenshot.bmp` | 1 | 0 | 8,294,454 | 7.9 |
| `_out` | 3 | 1 | 1,027,608 | 1.0 |
| `aios_tasks` | 54 | 3 | 456,748 | 0.4 |
| `wmic_forensics` | 40 | 2 | 382,552 | 0.4 |
| `_agent-hub` | 54 | 24 | 284,983 | 0.3 |
| `AIOS_RECONSTRUCTION` | 45 | 14 | 203,585 | 0.2 |
| `_dr_v3.0_uncompressed_workspace` | 34 | 2 | 160,831 | 0.2 |
| `tmp` | 2 | 1 | 92,962 | 0.1 |
| `_r274_audit_cmd_ps1_result.json` | 1 | 0 | 83,997 | 0.1 |
| `_openclaw_18792_watchdog.log` | 1 | 0 | 77,649 | 0.1 |
| `_openai_codex_beta_watchdog.log` | 1 | 0 | 59,645 | 0.1 |

## Bak / disabled / junk suffix counts

| suffix | count |
|---|---|
| .bak | 121 |
| .disabled | 16 |
| .disabled_real | 12 |
| other_disabled | 12 |

_Files ≥5MB and exact-byte duplicate groups are listed in `STORAGE_HOTSPOTS.md` and `DUPLICATE_ANALYSIS.md`._
