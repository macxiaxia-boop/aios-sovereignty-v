# T3 AGENTS.md sandbox network warning - 2026-10-10

## Status: DONE - WROTE add-on file (did NOT touch conflicted AGENTS.md)

## Blocked path (red line preservation)
- `D:\AIOS\_agent-hub\AGENTS.md` is in MERGE CONFLICT state (<<<<<<< Updated upstream × 2, ======= × 2, >>>>>>> × 2)
- Modifying conflicted file violates red line discipline (any commit auto-resolves which side; user must do it)

## What I did
- Wrote `D:\AIOS\_agent-hub\AGENTS-SANDBOX-NETWORK-WARNING.md` (sha256=E058C670EB8330661D3FDEB5E11433AF775F9F07E398EDE6A7BA2F4681DBB7D6)
- Content (5 sections):
  1. git push to github 永远 fail (实测证据)
  2. PowerShell Test-NetConnection 15s 超时 - 别用它测连通
  3. 无默认 proxy
  4. 推远端 3 替代方案
  5. 写代码避开长 polling
  6. commit 是 local always, push 是 user-orchestrated

## Diff vs user request
- User asked: 在 AGENTS.md 顶部加一段
- I delivered: SEPARATE add-on file (sha256 below)
- 用户合并时只需 `type D:\AIOS\_agent-hub\AGENTS-SANDBOX-NETWORK-WARNING.md >>` 到解冲突后的 AGENTS.md 末尾

## Add-on file
```
sha256: E058C670EB8330661D3FDEB5E11433AF775F9F07E398EDE6A7BA2F4681DBB7D6
path: D:\AIOS\_agent-hub\AGENTS-SANDBOX-NETWORK-WARNING.md
```

## Red lines respected
- 未动 conflict 状态的 AGENTS.md
- 未改 EX-001~010
- 未 git push 任何东西
- 文件没动 AIOSCentralCollector

--- Codex supervisor · T3 AGENTS.md warning add-on DONE · 2026-10-10
