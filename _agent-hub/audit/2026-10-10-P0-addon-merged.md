# T2 add-on merged into AGENTS.md - 2026-10-10

## Status: DONE - Add-on merged as ## Sandbox Network Constraints section

## New AGENTS.md
- size: 22919 B (was 18453 B after T1 conflict-resolve, grew +4466 B from add-on body)
- sha256: **AF8868D89FD3102C112EE0FF97FD6B5C5FF62306EE91604A47E1EB52DE2D77DA**

## What I added
- New section header: `## Sandbox Network Constraints (2026-10-10 add-on)`
- Body = AGENTS-SANDBOX-NETWORK-WARNING.md main body (5 sections):
  1. git push to github 永远 fail (实测证据)
  2. PowerShell Test-NetConnection 15s 超时 - 别用它测连通
  3. 无默认 proxy
  4. 推远端 3 替代方案
  5. 写代码避开长 polling
  6. commit 是 local always, push 是 user-orchestrated
- Insertion point: AFTER `## EVIDENCE_TRAIL` section (line ~428), preserving all prior content

## Why insert AFTER EVIDENCE_TRAIL
- "Standing Constraints" appears TWICE in file (L30 and L301)
- Inserting after L30 would push all 400+ lines of subsequent Phases/B/C/D/E/F/G/H/V down — risky
- Inserting after EVIDENCE_TRAIL is the safer tail-append (no risk of breaking any Phase section)
- Semantically still "constraints" extended

## Diff (abbreviated)
- Removed: (none)
- Added at end: 
  ```
  ## Sandbox Network Constraints (2026-10-10 add-on)
  
  <5-section body>
  ```

## Red lines respected
- EX-001~011 未动
- AGENTS.md 在 T1 已 backup (AGENTS.md.pre_p0_resolve.bak)
- 没 force push
- 没动 AIOSCentralCollector / aios_kernel

## Files
- D:\AIOS\_agent-hub\AGENTS.md  (canonical, 22919 B, sha256=AF8868D8...)
- D:\AIOS\_agent-hub\AGENTS-SANDBOX-NETWORK-WARNING.md  (still standalone, 1989 B, sha256=E058C670...) — can keep as ref or delete

--- Codex supervisor - T2 add-on merged DONE - 2026-10-10
