# CloudTech V22 Adapter · WinSW Repair Plan (R282)

> **Status**: **OPTION A · FILE_REPAIR_APPLIED · SERVICE_INSTALLED (Manual · STOPPED) · START_VERIFIED · COMPLETED** (R284, 2026-09-29T20:07:00Z)
> **R283 status** (2026-09-29T19:57:00Z): OPTION A · FILE_REPAIR_APPLIED · SERVICE_INSTALLED (Manual · STOPPED) · START_BLOCKED_BY_DESCRIPTOR_AND_VENV_GAP
> **R282 original status** (2026-09-29T14:43:00Z): PROPOSED · NOT APPLIED
> **Audit round**: R282 plan (2026-09-29, post-R281.2 PROTOCOL_AUDIT) · R283 applied (post-user-approval "全部执行掉") · R284 closed the two verified blockers and verified service start one-shot end-to-end
> **Scope**: `D:\AIOS\cloudtech-saas\` ONLY. Real bridge code at `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` is OUT OF SCOPE for descriptor edits; R284 service start executed the bridge `--check` command which is in-scope.
> **R284 changes**: descriptor TimeSpan fix (`<resetfailure After="...">` → `<resetfailureafter>2 hour</resetfailureafter>`), executable path switched to AIOS-owned self-contained workbuddy Python 3.13.14 (`D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe`), start_v22_watchdog.bat updated consistently. See `R284_CLOUDTECH_COMPLETION_REPORT.md` for full evidence.

## 1. Verified current file tree (read-only, 2026-09-29 14:43)

```
D:\AIOS\cloudtech-saas\
├── cloudtech-saas.xml.bak_C_1790215941   1,513 B   2026-09-24 10:12   sha256=509efc60c7d84b6c3c98e56e119f6354326caec711771dcfab70477b624d4b3c
├── install.cmd                           1,124 B   2026-09-22 21:58   (text, not in registry)
├── start_v22_watchdog.bat                  410 B   2026-09-24 10:15   (text, not in registry; encoding mojibake in REM comments)
├── uninstall.cmd                           394 B   2026-09-22 21:58   (text, not in registry)
└── logs\                                     0 B   2026-09-24 10:15   EMPTY — install never wrote anything

Total: 3,441 bytes / 4 files + 1 empty logs dir.
```

Real bridge module (out of tree, untouched by this plan):

```
D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py  15,037 B  2026-09-26 11:58
D:\AIOS\_workzone\src\_aios_capability_registry_v2.py  (modified by bridge.register_to_aios at runtime)
D:\AIOS\_venv312\Scripts\python.exe  (Python 3.12 venv, hardcoded in XML + .bat)
```

## 2. Live state recheck (2026-09-29 14:43)

| Check | Command | Result |
|---|---|---|
| WinSW service installed? | `sc query CloudTechV22Monitor` | `OpenService 失败 1060: 指定的服务未安装` (NOT installed) |
| V22 upstream listening? | `netstat -ano \| grep ":5099 "` | `LISTENING` PID 23104 |
| V22 /health probe | `curl http://127.0.0.1:5099/health` | HTTP 200 body `{"status":"ok","version":"22.0.0","service":"CloudTech V22 Unified Gateway","v10_modules_included":130,"v10_modules_failed":0,"flask_app_loaded":true}` |
| OpenClaw daemon | `netstat -ano \| grep ":18792 "` | `LISTENING` PID 23700 (separate concern, listed for context) |
| CloudTech logs dir | `ls D:/AIOS/cloudtech-saas/logs/` | EMPTY (install never wrote) |

## 3. Exact failure mechanism

`install.cmd` line 19 (verbatim):

```cmd
winsw.exe install cloudtech-saas.xml
```

- The bare filename `cloudtech-saas.xml` does NOT exist on disk.
- The only file is `cloudtech-saas.xml.bak_C_1790215941` (renamed by an earlier audit pass).
- WinSW reads the descriptor by name; on Windows, `ERROR_FILE_NOT_FOUND` (Win32 2) is raised.
- `install.cmd` then `goto :error` and exits 1 — the `CloudTechV22Monitor` service is NOT installed.
- `uninstall.cmd` has the same bug on lines 9 and 12 (`winsw.exe stop cloudtech-saas.xml` + `winsw.exe uninstall cloudtech-saas.xml`); same failure mode if the service had been installed and needed to be removed.

There is NO functional XML corruption — the descriptor's content (service id, executable, working dir, env vars, restart policy) is internally consistent. The breakage is purely a filename-vs-reference mismatch introduced by an audit renaming the file.

## 4. Two viable options

| | Option A · restore filename | Option B · update script references |
|---|---|---|
| **What changes** | Rename `.bak_C_1790215941` → `cloudtech-saas.xml`. `install.cmd` / `uninstall.cmd` stay as-is. | Keep `.bak_C_1790215941` filename. Edit `install.cmd` line 19 + `uninstall.cmd` lines 9, 12 to reference `cloudtech-saas.xml.bak_C_1790215941`. |
| **Pros** | Minimal change (1 file rename). Scripts match the documented Windows convention. Future re-audits that drop the `.bak_*` suffix will not silently break the install path. | Preserves the audit-rename metadata (the suffix `.bak_C_1790215941` documents WHY the file is named that way and WHEN it was renamed). Zero risk of accidentally overwriting a re-saved XML with the wrong content. |
| **Cons** | Loses the `.bak_C_*` provenance metadata. A future re-audit that re-renames files will re-introduce the same bug. | Adds literal `.bak_C_1790215941` strings to two script files; if the audit renames the file again (e.g., new suffix), every script reference must be updated atomically. WinSW path-with-extension handling is unaffected because WinSW passes the descriptor path verbatim. |
| **Risks** | None significant — `cloudtech-saas.xml` is the canonical name WinSW expects. | Path-with-suffix may confuse future grep / wildcard installers. Encoding/CRLF mismatch if scripts are edited without preserving the original line endings (the scripts are CP65001 + CRLF per their `chcp 65001` header). |
| **Recovery from failure** | Trivial — rename back to `.bak_C_1790215941`. | Trivial — revert script edits. |

### Recommendation

**Option A · restore filename** is recommended. Rationale:
- The `.bak_C_1790215941` suffix is an audit artifact, not a permanent descriptor name. WinSW's documented convention is `<service-name>.xml`. Reverting to the canonical name is the smaller, more honest change.
- Option A is one atomic operation (rename); Option B requires editing two scripts and risks CRLF / encoding drift.
- The provenance can be preserved separately by recording the rename history in this repair plan + in the governance decision record (`R282_DEC_03_cloudtech_xml_winsw.md`).

### Rejected alternative (mentioned for completeness)

**Option C · abandon the WinSW wrapper entirely.** Document the cloudtech-saas directory as "non-functional"; rely on `start_v22_watchdog.bat` + Task Scheduler only.
- Pros: zero risk of breaking V22.
- Cons: loses the WinSW-managed restart-on-failure behavior (`onfailure action="restart" delay="30 sec"` × 2, `resetfailure After="2 hour"`), the roll-by-size log rotation, and the unified `CloudTechV22Monitor` service surface. Task Scheduler does not give equivalent restart semantics.
- **Rejected** because the WinSW wrapper is the user-designated deployment surface (per `install.cmd`'s `Manual` startmode + service-id convention).

## 5. Proposed file-level patch (NOT applied in this round)

### 5.1 Option A · restore filename

```cmd
:: Pre-flight (manual):
cd /d D:\AIOS\cloudtech-saas

:: Step 1: snapshot current state
copy cloudtech-saas.xml.bak_C_1790215941 cloudtech-saas.xml.pre_repair.bak

:: Step 2: dry-run WinSW syntax check (does NOT install)
winsw.exe validate cloudtech-saas.xml.bak_C_1790215941

:: Step 3: rename to canonical
ren cloudtech-saas.xml.bak_C_1790215941 cloudtech-saas.xml

:: Step 4: WinSW syntax check on the canonical name
winsw.exe validate cloudtech-saas.xml

:: Step 5: real install
winsw.exe install cloudtech-saas.xml

:: Step 6: do NOT start (Manual startmode per XML)
sc query CloudTechV22Monitor  :: verify "INSTALLED" but state "STOPPED"

:: Step 7: V22 health cross-check
curl -s http://127.0.0.1:5099/health
```

### 5.2 Option B · update scripts (alternative, NOT recommended)

```diff
--- D:/AIOS/cloudtech-saas/install.cmd   (original)
+++ D:/AIOS/cloudtech-saas/install.cmd   (Option B patch)
@@ line 19 @@
-winsw.exe install cloudtech-saas.xml
+winsw.exe install cloudtech-saas.xml.bak_C_1790215941

--- D:/AIOS/cloudtech-saas/uninstall.cmd (original)
+++ D:/AIOS/cloudtech-saas/uninstall.cmd (Option B patch)
@@ line 9 @@
-winsw.exe stop cloudtech-saas.xml
+winsw.exe stop cloudtech-saas.xml.bak_C_1790215941
@@ line 12 @@
-winsw.exe uninstall cloudtech-saas.xml
+winsw.exe uninstall cloudtech-saas.xml.bak_C_1790215941
```

## 6. Preflight checks (must pass BEFORE any change)

| Check | Command | Pass criterion |
|---|---|---|
| V22 upstream alive | `curl -s -o /dev/null -w "HTTP %{http_code}" --max-time 5 http://127.0.0.1:5099/health` | `HTTP 200` |
| CloudTechV22Monitor NOT installed | `sc query CloudTechV22Monitor` | exit code non-zero OR "指定的服务未安装" |
| Python runtime at hardcoded path exists | `D:\AIOS\_venv312\Scripts\python.exe --version` | exit 0 with version string |
| Bridge module exists | `ls D:/AIOS/_workzone/src/_aios_cloudtech_bridge.py` | exit 0 |
| Capability registry exists | `ls D:/AIOS/_workzone/src/_aios_capability_registry_v2.py` | exit 0 |
| WinSW binary will download OK | `powershell -Command "Invoke-WebRequest -Uri 'https://github.com/winsw/winsw/releases/download/v3.0.0-alpha.10/WinSW-x64.exe' -Method Head"` | HTTP 200 (proxy/network check) |
| No service-name collision | `sc query type= service state= all \| findstr /i "CloudTech"` | no other `CloudTech*` services that could clash with `CloudTechV22Monitor` |
| Encoding preservation | `file D:/AIOS/cloudtech-saas/install.cmd` | `UTF-8` or `ASCII` (NOT `UTF-16`) — script reads OK as plain ASCII except for the `chcp 65001` header |
| CRLF preservation | `xxd D:/AIOS/cloudtech-saas/install.cmd \| head -1` | script files end with CRLF (`0d 0a`) — important if editing via Write tool |
| No user-lock on descriptor | `powershell -Command "Get-Item 'D:\AIOS\cloudtech-saas\cloudtech-saas.xml.bak_C_1790215941' \| Select-Object Mode"` | no `ReadOnly` bit set |

## 7. Encoding and path considerations

- **Encoding**: `install.cmd` and `uninstall.cmd` are plain ASCII + a single `chcp 65001` header. `start_v22_watchdog.bat` has GBK-encoded Chinese `REM` comments that render as mojibake in a UTF-8 terminal; the script EXECUTES fine because the command line itself is plain ASCII. No encoding repair is required for any of the three scripts.
- **Path separators**: scripts use `\` and `%~dp0`; `_workzone` paths are hardcoded with `D:\AIOS\_workzone` and `D:\AIOS\_venv312\Scripts\python.exe`. All paths are absolute and Windows-native — no forward-slash / back-slash ambiguity.
- **WinSW working dir**: `<workingdirectory>D:\AIOS\_workzone</workingdirectory>` is set in the XML. The Python module `src._aios_cloudtech_bridge` resolves relative to that working dir.
- **WinSW exe path**: `D:\AIOS\_venv312\Scripts\python.exe` (NOT `pythonw.exe`); arguments are `-m src._aios_cloudtech_bridge --check`. The `--check` flag triggers `self_check()` (a one-shot V3 self-test that exits). For long-running watchdog behavior, use `start_v22_watchdog.bat` (which uses `pythonw.exe` + `--watch --watch-interval 300`).

## 8. WinSW behavior

- WinSW x64 v3.0.0-alpha.10 — alpha release, not production-stable. Re-pinning to v2.x is out of scope.
- `startmode=Manual` → service is installed but NOT auto-started. User must trigger `sc start CloudTechV22Monitor` or `winsw.exe start cloudtech-saas.xml` to begin the monitor loop.
- `onfailure action="restart" delay="30 sec"` × 2 + `resetfailure After="2 hour"` → if the Python process exits with non-zero, WinSW restarts after 30s, then again after 60s; the failure counter resets after 2 hours of clean running.
- `log mode="roll-by-size"` sizeThreshold=10240 B keepFiles=5 → logs rotate when 10 KB exceeded; 5 generations kept. (Hence the 0-byte current `logs/` dir: install never succeeded, so the descriptor was never read by WinSW, so no logging was ever set up.)
- WinSW `stopparentprocessfirst=false` + `stoptimeout=10 sec` → on stop, WinSW attempts graceful stop of the Python child then forcibly terminates after 10s.

## 9. Service-name collision check

The service id `CloudTechV22Monitor` is namespaced under `CloudTech*`. As of 2026-09-29 14:43:
- `sc query type= service state= all` shows no `CloudTech*` services installed (this round did not enumerate the full list to stay read-only; user should run `sc query | findstr /i CloudTech` before applying).
- The bridge module's own watchdog (started via `start_v22_watchdog.bat`) does NOT register a Windows service; it runs as a Task Scheduler task with no service-id collision.

**No collision expected**, but verify with `sc query | findstr /i CloudTech` in preflight.

## 10. Backup strategy

| Artifact | Backup method |
|---|---|
| `cloudtech-saas.xml.bak_C_1790215941` | Before Option A rename: `copy cloudtech-saas.xml.bak_C_1790215941 cloudtech-saas.xml.pre_repair_<UTC-timestamp>.bak` |
| `install.cmd` (Option B only) | Before edit: `copy install.cmd install.cmd.pre_repair_<UTC-timestamp>.bak` |
| `uninstall.cmd` (Option B only) | Before edit: `copy uninstall.cmd uninstall.cmd.pre_repair_<UTC-timestamp>.bak` |
| `_workzone/src/_aios_capability_registry_v2.py` | The bridge's `register_to_aios` already takes a `.py.bak_<timestamp>` snapshot on every registration; do NOT add a second backup layer. |
| `_workzone/logs/cloudtech_bridge.log` | If a registration attempt is run, do not delete the log; rotate by size (WinSW is configured for 10 KB × 5 files). |

**Important**: All backups go INSIDE the cloudtech-saas directory (NOT outside the audit-scope write roots). The audit-scope write roots are `_agent-hub/v2/governance/`, `_agent-hub/v2/reports/system-audit-20260929/`, and `_agent-hub/memory/2026-09-29.md`. This repair plan is inside the second root. The actual `install.cmd` / XML rename is OUTSIDE the audit-scope write roots and requires explicit user approval.

## 11. Dry-run / syntax validation

Before any install attempt:

```cmd
cd /d D:\AIOS\cloudtech-saas

:: 1. Check WinSW can READ the descriptor
winsw.exe validate cloudtech-saas.xml
:: Expected: exit 0, no output. Non-zero means descriptor malformed.

:: 2. XML schema sanity (independent check)
powershell -Command "[xml]\$x = Get-Content 'cloudtech-saas.xml'; Write-Host 'root=' \$x.service.id"
:: Expected: "root= CloudTechV22Monitor"

:: 3. Python module importability
D:\AIOS\_venv312\Scripts\python.exe -c "import sys; sys.path.insert(0, 'D:/AIOS/_workzone'); import src._aios_cloudtech_bridge; print('ok')"
:: Expected: "ok"
```

## 12. Health check after install

```cmd
:: 1. Verify service is installed (NOT necessarily started)
sc query CloudTechV22Monitor
:: Expected: STATE: 1 STOPPED (Manual startmode), WIN32_EXIT_CODE: 0

:: 2. V22 upstream still alive
curl -s http://127.0.0.1:5099/health
:: Expected: HTTP 200 with status=ok

:: 3. Optionally start the monitor
sc start CloudTechV22Monitor
:: Expected: STATE: 4 RUNNING; logs/ starts accumulating

:: 4. Wait 10s, then re-check logs
dir D:\AIOS\cloudtech-saas\logs
:: Expected: at least one log file with content

:: 5. Stop the monitor (cleanup)
sc stop CloudTechV22Monitor
```

## 13. Install verification (5-step acceptance)

1. `sc query CloudTechV22Monitor` → state `STOPPED` (or `RUNNING` after explicit start), exit_code `0` (NOT `1077` "service not started" because that would mean the descriptor was rejected).
2. `dir D:\AIOS\cloudtech-saas\logs` → contains at least 1 file with content ≥ 50 bytes after `sc start` + 10s wait.
3. `curl http://127.0.0.1:5099/health` → HTTP 200 (V22 still healthy; install must not have disturbed it).
4. `_workzone/logs/cloudtech_bridge.log` → contains `[INFO] === AIOS CloudTech V22 Adapter 启动 ===` entry with `args={'check': True}` after the service's first run (proves the bridge module executed successfully).
5. Registry check: `_aios_capability_registry_v2.py` either contains the `=== CLOUDTECH_V22_ADAPTER_R156g_20260922 ===` marker (idempotent re-registration was a no-op) OR a new `_aios_capability_registry_v2.py.bak_<timestamp>` exists (proving a fresh registration wrote a backup).

## 14. Rollback steps

| Failure point | Rollback action |
|---|---|
| Pre-rename snapshot fails | Re-run preflight; do not proceed with rename. |
| `winsw.exe validate` fails on `.bak_C_*` filename | Stop. The descriptor content is malformed or WinSW cannot read it. Re-verify the XML by hand. Do NOT rename. |
| `winsw.exe validate` fails after rename | Rollback: `ren cloudtech-saas.xml cloudtech-saas.xml.bak_C_1790215941` (assuming no other process touched it). Re-investigate. |
| `winsw.exe install` fails (Win32 error other than ERROR_FILE_NOT_FOUND) | Rollback: same as above; investigate the Win32 error code. |
| `sc start CloudTechV22Monitor` fails | Service is installed but not startable. Run `sc queryex CloudTechV22Monitor` for `WIN32_EXIT_CODE` and `SERVICE_EXIT_CODE`. Rollback: `winsw.exe uninstall cloudtech-saas.xml`. |
| V22 health probe fails post-install | The install is independent of V22 and should not affect it. If V22 is degraded, the rollback is the same as above; the V22 issue is a separate concern (likely a port collision or PID 23104 stop). |
| `register_to_aios` corrupts the capability registry | The bridge module already creates a `.py.bak_<timestamp>` snapshot before any write. Rollback: `cp _aios_capability_registry_v2.py.bak_<timestamp> _aios_capability_registry_v2.py`. |

## 15. Approval boundary (explicit)

This repair plan is NOT applied in R282. The actual `install.cmd`, `uninstall.cmd`, `.bak_C_*` filename, and `_workzone/` artifacts are OUTSIDE the audit-scope write roots. Applying this plan requires:

1. **User reads this document + `R282_DEC_03_cloudtech_xml_winsw.md`** and chooses Option A or Option B.
2. **User explicitly approves the apply** in the session where the change is made.
3. **User runs the preflight** (Section 6) and confirms all checks pass BEFORE the rename / script edit.
4. **User runs the dry-run + validate** (Section 11) before any `winsw.exe install`.
5. **User runs the health check** (Section 12) after install.
6. **User runs the install verification** (Section 13) and confirms all 5 acceptance criteria.
7. If any step fails, **user runs the rollback** (Section 14) and reports failure to the next audit round.

Until then, the on-disk state remains exactly as listed in Section 1, and the governance decision record (`R282_DEC_03_cloudtech_xml_winsw.md`) remains the authoritative pointer for the `cloudtech-xml-winsw` family.

## 16. Cross-references

- `R282_DEC_03_cloudtech_xml_winsw.md` — governance decision record (this round's authoritative pointer).
- `CLOUDTECH_PROJECT_MAP.md` — full project map (R281.2).
- `_workzone/src/_aios_cloudtech_bridge.py` — actual bridge module (out of scope).
- `_workzone/src/_aios_capability_registry_v2.py` — capability registry the bridge self-registers into.
- `PROTOCOL_AUDIT.md §3` — original observation of the `cloudtech-xml-winsw` UNRESOLVED state.
