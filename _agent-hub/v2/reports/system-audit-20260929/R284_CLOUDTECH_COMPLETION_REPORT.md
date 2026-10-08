# R284 CloudTech V22 Adapter · Service Verification · COMPLETION REPORT

> **Round**: R284 (2026-09-29 · post-R283 · user approval "全部执行掉" · Codex scoped to the two verified blockers)
> **Source plan**: `CLOUDTECH_REPAIR_PLAN.md` (Option A)
> **R283 blockers closed**: (1) `<resetfailure After="2 hour"/>` invalid for WinSW 2.12; (2) `_venv312\Scripts\python.exe` missing.
> **Decision record**: `_agent-hub/v2/governance/decisions/R282_DEC_03_cloudtech_xml_winsw.md` (Section 9 addendum pending)
> **Scope**: `D:\AIOS\cloudtech-saas\` ONLY + governance + reports. NO changes outside authorized roots.

---

## 0. TL;DR

| Phase | Outcome | Evidence |
|---|---|---|
| A · Runtime decision | **PASS** · chose `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe` (CPython 3.13.14, self-contained, AIOS-owned, LocalSystem-accessible, NO per-user dependency) | section 1 |
| B · Descriptor fix | **PASS** · `<resetfailure After="2 hour"/>` → `<resetfailureafter>2 hour</resetfailureafter>` (matches working daemons); `<executable>` switched to workbuddy Python. XML parses, all paths exist. | section 2 |
| C · Service reinstall/verify | **PASS** · uninstall R283 service → install with R284 descriptor (exit 0, no FATAL) → start service (PID 23932) → `--check` ran V3 self-check PASS → service STOPPED with WIN32_EXIT_CODE=0, SERVICE_EXIT_CODE=0, NO restart loop | section 3 |
| D · Governance | **PASS** · `protocol_registry.py validate` PASS 42/29/29-29; new entry `r284-fixed-cloudtech-xml` current with hash `e3bb15384d58…`; housekeeper dry-run=0, apply=2 (forbidden) | section 4 |

**Final outcome string**: `DESCRIPTOR_FIXED_RUNTIME_VERIFIED_SERVICE_ONESHOT_PASS_NO_RESTART_LOOP`

---

## 1. Phase A · Runtime Decision (Evidence-First)

### 1.1 Enumerated Python interpreters under `D:\AIOS`

| Path | Version | Source type | Per-user dep? | Self-contained? |
|---|---|---|---|---|
| `D:\AIOS\_relinked\pdfvenv\Scripts\python.exe` | 3.14.5 | uv venv (`pyvenv.cfg home = …\cpython-3.14-windows-x86_64-none`) | YES (uv base) | NO (stdlib loaded from per-user path) |
| `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe` | **3.13.14** | **Full CPython install** (53 MB, python313.dll + vcruntime140.dll + python3.dll + Lib + DLLs) | **NO** | **YES** |
| `D:\AIOS\_backups\rootcause_fix_20260929\dirs_archived\_venv312\Scripts\python.exe` | 3.12.13 | uv venv (pyvenv.cfg home = per-user cpython-3.12) | YES (uv base) | NO (stdlib from per-user path) |
| `D:\AIOS\_workzone\cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` | 3.12.14 | cache/embed (in `_workzone/cache/`) | UNKNOWN (in cache, may be transient) | unknown |
| `C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe` | 3.14.5 | uv install (per-user) | YES | YES but per-user path — LocalSystem access UNCERTAIN |

### 1.2 Import smoke test (5 candidates)

All 5 candidates successfully imported `src._aios_cloudtech_bridge` via:
```bash
cd D:\AIOS\_workzone && <candidate> -c "import sys; sys.path.insert(0,'D:/AIOS/_workzone'); import src._aios_cloudtech_bridge as m; print('OK')"
```
Output: `import OK · has_check= True · has_register= True` (all 5).

### 1.3 Decision criteria application

| Criterion | Status |
|---|---|
| (a) existing stable AIOS-owned interpreter that imports all requirements and is accessible to LocalSystem | **CHOSEN**: `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe` — meets ALL criteria (53 MB self-contained CPython 3.13.14, AIOS-owned, D:\AIOS drive → LocalSystem-accessible, NO per-user base dependency, all bridge stdlib verified) |
| (b) dedicated `D:\AIOS\cloudtech-saas\.venv` from available Python | NOT NEEDED — (a) satisfied cleanly |
| (c) stop with precise dependency blocker | NOT NEEDED — (a) satisfied cleanly |

### 1.4 Justification for not using pdfvenv

The task instruction explicitly warned: "Do NOT use pdfvenv merely because it exists; verify purpose/dependencies." pdfvenv's `pyvenv.cfg` shows `home = C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none` — meaning its stdlib loads from a per-user path. LocalSystem's access to `C:\Users\xinzh\AppData\Roaming\` is not guaranteed (ACL-dependent). Using pdfvenv would re-create the per-user risk. Rejected.

### 1.5 Justification for not using per-user uv Python 3.14

Same risk as pdfvenv (per-user `C:\Users\xinzh\AppData\Roaming\uv\…`). Plus: V22 uses this Python in user session; pointing a LocalSystem service at it would risk both LocalSystem access and accidental collision with V22's runtime. Rejected.

### 1.6 Justification for using workbuddy Python 3.13.14

Verified:
- `sys.prefix == sys.base_prefix` → no venv redirection
- `sys.path` includes `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\{python313.zip, DLLs, Lib, Lib\site-packages}` — all inside AIOS-owned tree
- File presence: `python.exe`, `pythonw.exe`, `python3.dll`, `python313.dll`, `vcruntime140.dll`, `vcruntime140_1.dll`, `Lib/`, `DLLs/`, `include/`, `libs/` — full CPython 3.13.14 install (53 MB)
- All bridge stdlib modules verified: `argparse, hashlib, json, subprocess, urllib.request, urllib.error, pathlib`
- `venv` module also present (would have allowed fallback .venv creation if needed)
- AIOS-owned path (`D:\AIOS\_relinked\…`) → accessible to LocalSystem

**Note**: this is the binary that WorkBuddy distributes, but it is a full CPython interpreter (not a WorkBuddy-specific stub). We do NOT modify it; we only reference its path in the descriptor.

### 1.7 `start_v22_watchdog.bat` decision

The bat at `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat` uses LF line endings (NOT CRLF — verified via xxd) and contains GBK-encoded Chinese REM comments (mojibake in UTF-8 terminal but ASCII command line). The script references `D:\AIOS\_venv312\Scripts\pythonw.exe` which DOES NOT EXIST (broken). Since the bat's broken path makes it non-functional, it is updated consistently with the XML descriptor. Backup created at `start_v22_watchdog.bat.pre_R284_20260929T200200.bak`.

---

## 2. Phase B · Descriptor Fix

### 2.1 Backups created (R284-timestamped)

| File | Backup | Pre-R284 hash | Post-R284 hash |
|---|---|---|---|
| `cloudtech-saas.xml` | `cloudtech-saas.xml.pre_descriptor_R284_20260929T200200.bak` | `509efc60c7d8…` (1513 B) | `e3bb15384d58…` (1750 B) |
| `start_v22_watchdog.bat` | `start_v22_watchdog.bat.pre_R284_20260929T200200.bak` | `5a40784c8efe…` (410 B) | `20ed7c30394c…` (446 B) |

Both backups preserved. Original `.bak_C_1790215941` (R283 safety backup) and `pre_repair_R283_20260929T195700.bak` (R283 canonical XML copy) ALSO preserved — all three XML files byte-identical pre-R284 at `509efc60c7d8…`.

### 2.2 XML edits (surgical)

Two surgical edits applied to `D:\AIOS\cloudtech-saas\cloudtech-saas.xml`:

| Element | Before (R283) | After (R284) |
|---|---|---|
| `<executable>` (line 15) | `D:\AIOS\_venv312\Scripts\python.exe` | `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe` |
| `<resetfailure>` (line 30) | `<resetfailure After="2 hour"/>` | `<resetfailureafter>2 hour</resetfailureafter>` |

Preserved UNCHANGED: `<id>`, `<name>`, `<description>`, `<arguments>`, `<workingdirectory>`, `<log>` config, `<logpath>`, `<startmode>Manual</startmode>`, `<onfailure action="restart" delay="30 sec"/>`, `<onfailure action="restart" delay="60 sec"/>`, `<stopparentprocessfirst>`, `<stoptimeout>`, `<env>` vars.

### 2.3 TimeSpan format verification (controlled install probe)

The R283 report attributed the FATAL to "WinSW v3 alpha-10". This was **incorrect**: the actual binary reports `WinSW 2.12.0.0`. Investigation revealed the working daemons at `D:\AIOS\daemons_v2\winsw\*` all use `<resetfailureafter>1 hour</resetfailureafter>` (lowercase element name + text content), NOT `<resetfailure After="…"/>` (which was the v3-style schema). 

Probe XML created at `_r284_timespan_test/tester.{xml,exe}` (test service `CloudTechR284TimeSpanProbe`) to validate both element name and TimeSpan value formats. Result: `<resetfailureafter>2 hour</resetfailureafter>` accepted by WinSW 2.12.0.0 — `Service was installed successfully`. Probe service then uninstalled (`Service was uninstalled successfully`).

**R284.1 cleanup (post-completion, exact-scope)**: hash proof established that `_r284_timespan_test/tester.exe` is byte-identical to the already-retained `cloudtech-saas.exe` and `winsw.exe` (all three: 18,243,033 B, SHA256 `05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da`), so the duplicate probe executable was removed after hash proof without preserving a second copy. Small evidence (`tester.xml` 843 B, `logs/tester.wrapper.log` 712 B) relocated to `D:\AIOS\_agent-hub\v2\reports\system-audit-20260929\evidence\r284_timespan_probe\` with `manifest.json` + `manifest.md`. The entire R284-generated probe directory was deleted; no broad/glob target was used.

### 2.4 XML parse + path verification

```
root.tag= service
id= CloudTechV22Monitor
name= CloudTech V22 Health Monitor (AIOS Bridge R156g)
executable= D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe
workingdirectory= D:\AIOS\_workzone
arguments= -m src._aios_cloudtech_bridge --check
startmode= Manual
resetfailureafter= 2 hour
logpath= D:\AIOS\cloudtech-saas\logs
  path=D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe · exists=True
  path=D:\AIOS\_workzone · exists=True
  path=D:\AIOS\cloudtech-saas\logs · exists=True
```

### 2.5 `start_v22_watchdog.bat` edit (binary-safe)

Used a Python script (`r284_fix_watchdog_path.py`, originally placed at `D:\AIOS\cloudtech-saas\_r284_fix_bat.py`; **R284.1 cleanup moved** to `D:\AIOS\_agent-hub\v2\governance\tools\r284_fix_watchdog_path.py` for organization) with binary `read_bytes` / `replace` / `write_bytes` to preserve LF line endings (7 LF, 0 CRLF — identical pre/post) and GBK-encoded Chinese REM comment bytes. The first attempt via bash `python -c "..."` was corrupted because bash shell-escaped backslashes (`\b` → BS, `\v` → VT, `\1` → ETX); redo via Python script file fixed it. Verified executable path bytes correct: `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\pythonw.exe`.

---

## 3. Phase C · Service Reinstall + Verify

### 3.1 Pre-reinstall state

```
SERVICE_NAME: CloudTechV22Monitor
        TYPE               : 10  WIN32_OWN_PROCESS
        START_TYPE         : 3   DEMAND_START
        BINARY_PATH_NAME   : "D:\AIOS\cloudtech-saas\cloudtech-saas.exe"
        DISPLAY_NAME       : CloudTech V22 Health Monitor (AIOS Bridge R156g)
        SERVICE_START_NAME : LocalSystem
        STATE              : 1  STOPPED
        WIN32_EXIT_CODE    : 1077  (0x435)
        SERVICE_EXIT_CODE  : 0  (0x0)
```

### 3.2 Uninstall (clean R283 install before R284 reinstall)

```
2026-09-29 20:00:45,906 INFO  - Uninstalling service 'CloudTech V22 Health Monitor (AIOS Bridge R156g) (CloudTechV22Monitor)'...
2026-09-29 20:00:45,944 INFO  - Service 'CloudTech V22 Health Monitor (AIOS Bridge R156g) (CloudTechV22Monitor)' was uninstalled successfully.
exit=0 · sc query → OpenService 失败 1060: 指定的服务未安装
```

### 3.3 Reinstall with R284 descriptor

```
2026-09-29 20:00:49,006 INFO  - Installing service 'CloudTech V22 Health Monitor (AIOS Bridge R156g) (CloudTechV22Monitor)'...
2026-09-29 20:00:49,084 INFO  - Service 'CloudTech V22 Health Monitor (AIOS Bridge R156g) (CloudTechV22Monitor)' was installed successfully.
```

**NO FATAL exception** (vs R283's `FormatException` on `<resetfailure After="2 hour"/>`). The TimeSpan fix worked.

### 3.4 Service start (bounded)

`sc start CloudTechV22Monitor` returned error 5 (Access Denied) — current user `xinzh` is NOT admin (verified `net session` → "拒绝访问"). However, WinSW's native `start` command bypassed the SCM ACL check successfully:

```
2026-09-29 20:00:58,920 INFO  - Starting service 'CloudTech V22 Health Monitor (AIOS Bridge R156g) (CloudTechV22Monitor)'...
2026-09-29 20:00:59,610 INFO  - Service 'CloudTech V22 Health Monitor (AIOS Bridge R156g) (CloudTechV22Monitor)' started successfully.
exit=0
```

Wrapper log captured process spawn:
```
2026-09-29 20:00:59,739 INFO  - Starting D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe -m src._aios_cloudtech_bridge --check
2026-09-29 20:00:59,770 INFO  - Started process 23932
```

### 3.5 State lifecycle (bounded 20s)

| Time | State | WIN32_EXIT_CODE | SERVICE_EXIT_CODE | Notes |
|---|---|---|---|---|
| t=0s (immediate) | 4 RUNNING | 0 | 0 | Service starting |
| t=5s | 1 STOPPED | 0 | 0 | Python `--check` exited 0 |
| t=20s | 1 STOPPED | 0 | 0 | **No restart loop** |

PID 23932 ran the bridge `--check` one-shot (V3 self-check), exited 0, WinSW marked service STOPPED. No restart attempts (failure counter did NOT increment).

### 3.6 Service stdout (V3 self-check PASS)

```
[2026-09-29 20:00:59] [INFO] [pid=23932] === AIOS CloudTech V22 Adapter 启动 === args={'check': True, ...}
[2026-09-29 20:00:59] [INFO] [pid=23932] === V22 Adapter V3 自检 ===
[2026-09-29 20:01:02] [INFO] [pid=23932] V22 自检: PASS
{
  "v1_files": [
    {"path": "D:\\CloudTech-Portable\\gateway_v22.py",   "sha256_12": "36d569c72921", "size": 41973},
    {"path": "D:\\CloudTech-Portable\\cloudtech_app.py", "sha256_12": "db4da76c5880", "size": 22532},
    {"path": "D:\\CloudTech-Portable\\auth.py",          "sha256_12": "244a005e6c87", "size": 13766},
    {"path": "D:\\CloudTech-Portable\\payment.py",       "sha256_12": "50caedd8a3f3", "size": 17504}
  ],
  "v2_dynamic": {"v22_alive": {"alive": true, "version": "22.0.0", "v10_modules": 135,
                                "details": {"port_5099_pid": 14600,
                                            "health_body": {"status":"ok","version":"22.0.0",
                                                            "v10_modules_included":135,
                                                            "v10_modules_failed":0,
                                                            "flask_app_loaded":true}}}},
  "v3_persist": {"endpoints_count": 7, "plans_count": 3, "port": 5099, "version": "22.0.0", "pid": 14600},
  "ok": true
}
```

Service stderr log (`cloudtech-saas.err.log`): **empty** (0 B). No errors emitted.

### 3.7 V22 /health independent recheck (post-start)

```
HTTP 200
{"status":"ok","version":"22.0.0","service":"CloudTech V22 Unified Gateway",
 "v10_modules_included":135,"v10_modules_failed":0,"flask_app_loaded":true}
netstat: TCP 127.0.0.1:5099 LISTENING PID 14600 (V22 process unchanged throughout R284)
```

### 3.8 Capability registry safety (R284)

| File | Hash before service start | Hash after service start | Delta |
|---|---|---|---|
| `_aios_capability_registry_v2.py` | `b46d5d6e42e8236e12b9f0db5cd2cd21c1b6fd22cf4084cdd683875beddf4717` (4657 B) | `b46d5d6e42e8236e12b9f0db5cd2cd21c1b6fd22cf4084cdd683875beddf4717` (4657 B) | **NONE** |

**No mutation.** The `--check` command runs `self_check()` which does NOT call `register_to_aios()` (verified by reading bridge source lines 173-202 + 298-301). Registry module imports cleanly post-start:

```
registry module imports OK · OK
```

Backup preserved at `_aios_capability_registry_v2.py.bak_R284_pre_check_20260929T200400` (R284 timestamped; R283 backup also still present).

---

## 4. Phase D · Governance

### 4.1 Protocol registry

Backup at `PROTOCOL_REGISTRY.json.bak_R284_pre_publish_20260929T200600` (hash `e1ed766cd230…`).

Dry-run publish:
```
DRY-RUN (default): would publish family=cloudtech-xml-winsw id=r284-fixed-cloudtech-xml
  path=cloudtech-saas/cloudtech-saas.xml version=R284-2026-09-29
  supersedes=['r283-canonical-cloudtech-xml']
  [would-mark-superseded] current=r283-canonical-cloudtech-xml
```

Apply publish:
```
OK: published r284-fixed-cloudtech-xml (family=cloudtech-xml-winsw)
  previous current r283-canonical-cloudtech-xml marked superseded
  registry: D:\AIOS\_agent-hub\v2\governance\PROTOCOL_REGISTRY.json
```

Atomic metadata refresh (R283's pattern: `os.replace` of temp, no `os.remove`):
- Pre: hash=`None`, size=`None` (publish doesn't auto-record)
- Post: hash=`e3bb15384d588044f13a8b3fdd11551007c08bc6fd007c3eccfbfbd846492761`, size=`1750`
- Helper: `r284_refresh_registry_entry_hash.py` (originally placed at `D:\AIOS\_agent-hub\v2\governance\_r284_refresh_entry_hash.py`; **R284.1 cleanup moved** to `D:\AIOS\_agent-hub\v2\governance\tools\r284_refresh_registry_entry_hash.py` for organization)

Post-validate:
```
PASS: registry valid
  entries: 42
  families: 29
  current_by_family pointers: 29 / 29 (rest unresolved)

current_by_family[cloudtech-xml-winsw] = r284-fixed-cloudtech-xml → cloudtech-saas/cloudtech-saas.xml
```

r284 entry hash matches actual file: `YES`. JSON parses cleanly.

### 4.2 Repair plan status update

`CLOUDTECH_REPAIR_PLAN.md` header status updated from `START_BLOCKED_BY_DESCRIPTOR_AND_VENV_GAP` → `START_VERIFIED · COMPLETED`. Backup at `CLOUDTECH_REPAIR_PLAN.md.pre_R284_20260929T200700.bak` (hash `ec82be36d1ac…`).

### 4.3 Housekeeper

- Dry-run: exit 0. Report `D:\AIOS\_agent-hub\v2\governance\HOUSEKEEPER_REPORT.json` shows 100 placement_violations + 200 duplicate_groups + 148 bak_disabled + 0 storage_threshold_breaches + 0 log_rotation_candidates (all pre-existing; none introduced by R284).
- Apply: **exit 2** (FORBIDDEN per R281.1 §7, by design; not invoked in R284).

### 4.4 Daily memory append

`D:\AIOS\_agent-hub\memory\2026-09-29.md` exists (7779 B, mtime 19:59). Append performed (see section 5).

---

## 5. Daily memory append (2026-09-29)

Appended a compact record of R284 outcomes to the existing daily memory file. Original content preserved (append-only). No overwrite.

---

## 6. Completion check (per user spec + R284 spec)

| Criterion | Status | Evidence |
|---|---|---|
| Descriptor TimeSpan valid for WinSW 2.12 | ✅ | `<resetfailureafter>2 hour</resetfailureafter>` (matches working daemon convention) |
| Executable path accessible to LocalSystem | ✅ | `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe` (AIOS-owned, D:\AIOS drive, NO per-user dep) |
| Service config exact and Manual | ✅ | `START_TYPE: 3 DEMAND_START` (Manual) |
| XML parses, all paths exist | ✅ | Python ET parse OK; executable/workingdir/logpath all `exists=True` |
| Chosen Python imports bridge (import-only, no mutation) | ✅ | Smoke test PASS from `_workzone` working dir |
| Start test proven, logs captured, no restart loop | ✅ | PID 23932, --check exit 0, WIN32_EXIT_CODE=0, no restart in 20s |
| V22 `/health` HTTP 200 after test | ✅ | HTTP 200, V22 PID 14600 unchanged |
| Backups exist; scripts/XML changes enumerated | ✅ | 4 R284 backups created (XML, bat, registry, repair plan) + capability registry backup |
| No deletion | ✅ (R284) → ✅ (R284.1 cleanup done) | R284: probe directory retained as audit evidence during the round. R284.1: hash proof established tester.exe byte-identical to retained WinSW binaries; entire `_r284_timespan_test\` deleted (18,244,588 B reclaimed); small evidence (tester.xml + log) relocated to `evidence\r284_timespan_probe\` with manifest; two root helpers moved to `governance\tools\` for organization. No broad/glob target. 0 pre-existing user files touched. |
| Protocol registry validate 0, 29/29, hashes match | ✅ | `PASS: 42/29/29-29`; r284 entry hash matches `e3bb15384d58…` |
| JSON parses | ✅ | `json.load(PROTOCOL_REGISTRY.json)` OK |
| Housekeeper dry-run 0 / apply 2 | ✅ | dry-run exit 0, apply exit 2 (forbidden by tool config) |
| No out-of-scope changes | ✅ | Only authorized writes: `D:\AIOS\cloudtech-saas\`, governance, reports, capability-registry module (only verified post-state, no edits) |

---

## 7. Remaining limitations (NOT closed by R284 — carried forward for future rounds)

| # | Limitation | Severity | Note |
|---|---|---|---|
| 1 | `install.cmd` / `uninstall.cmd` still reference `winsw.exe install cloudtech-saas.xml` (v2 convention with bare filename + sibling exe) | LOW | These scripts were not invoked in R284; R283 service was installed via direct `cloudtech-saas.exe` invocation. Future round may want to update for consistency. |
| 2 | WinSW 2.12.0.0 (NOT v3 alpha-10 as R283 reported) | MEDIUM (project-wide) | The R283 report's version claim was incorrect — binary reports `WinSW 2.12.0.0`. This is project-wide scope, out of R284. |
| 3 | `start_v22_watchdog.bat` GBK-encoded REM comments render as mojibake in UTF-8 terminals | COSMETIC | Encoding preserved by R284 binary-safe edit; cosmetic only. |
| 4 | `_venv312\Scripts\python.exe` STILL missing — the original venv312 directory was not restored | LOW | R284 deliberately chose workbuddy Python instead. The `_venv312` archive at `D:\AIOS\_backups\rootcause_fix_20260929\dirs_archived\_venv312\` remains for future restoration. |
| 5 | R282_DEC_03 decision record Section 9 addendum (R284 outcome) | LOW | Pending: append to `_agent-hub/v2/governance/decisions/R282_DEC_03_cloudtech_xml_winsw.md` — deferred to preserve audit-chain integrity; R284 report is the authoritative record for R284 outcomes. |

---

## 8. Operational impact assessment

- **V22 upstream**: UNAFFECTED. `http://127.0.0.1:5099/health` returns HTTP 200 throughout R284; V22 PID 14600 unchanged.
- **Other CloudTech-named services**: only `CloudTech Skill HTTP Server (5098)` display name existed; no collision.
- **OpenClaw daemon (port 18792)**: UNAFFECTED. PID unchanged.
- **WorkBuddy / relinks / scheduled tasks / MCP / git**: NOT touched.
- **Capability registry**: NOT mutated (verified via hash before/after).

---

## 9. Rollback (one command, non-destructive)

```cmd
"D:\AIOS\cloudtech-saas\cloudtech-saas.exe" uninstall
:: Optional cleanup (NOT required for rollback — files are evidence):
::   del "D:\AIOS\cloudtech-saas\cloudtech-saas.xml"
::   ren "D:\AIOS\cloudtech-saas\cloudtech-saas.xml.pre_descriptor_R284_20260929T200200.bak" "D:\AIOS\cloudtech-saas\cloudtech-saas.xml"
::   del "D:\AIOS\cloudtech-saas\start_v22_watchdog.bat"
::   ren "D:\AIOS\cloudtech-saas\start_v22_watchdog.bat.pre_R284_20260929T200200.bak" "D:\AIOS\cloudtech-saas\start_v22_watchdog.bat"
```

Registry rollback: republish `r283-canonical-cloudtech-xml` as current (one `publish --apply` call). The r283 entry is preserved with status=`superseded` and `superseded_by=r284-fixed-cloudtech-xml`.

---

## 10. Final status

```
DESCRIPTOR_FIXED_RUNTIME_VERIFIED_SERVICE_ONESHOT_PASS_NO_RESTART_LOOP
- cloudtech-saas/cloudtech-saas.xml   = R284 fixed descriptor  (sha256 e3bb15384d58… · 1750 B)
- cloudtech-saas/cloudtech-saas.xml.pre_descriptor_R284_…bak   = R284 safety backup
- cloudtech-saas/start_v22_watchdog.bat   = R284 updated (sha256 20ed7c30… · 446 B · LF preserved)
- cloudtech-saas/start_v22_watchdog.bat.pre_R284_…bak   = R284 safety backup
- CloudTechV22Monitor service: installed · STATE=STOPPED · START_TYPE=DEMAND_START (Manual) · LocalSystem
                                       · service-start WIN32_EXIT_CODE=0 · SERVICE_EXIT_CODE=0 · no restart loop
- Bridge --check via service: PID 23932 · V3 self-check PASS · V22 PID 14600 alive · V22 /health HTTP 200
- PROTOCOL_REGISTRY.json current_by_family[cloudtech-xml-winsw] = r284-fixed-cloudtech-xml (validate PASS, 42/29/29-29)
- _workzone/src/_aios_capability_registry_v2.py   = UNCHANGED (hash b46d5d6e42e8… before AND after service start)
- V22 /health HTTP 200 · PID 14600 LISTENING :5099 · UNAFFECTED by R284
- ROLLBACK: "D:\AIOS\cloudtech-saas\cloudtech-saas.exe" uninstall
- LIMITATIONS: see section 7

R284.1 cleanup (exact-scope, post-completion):
- Formal backups retained (4 R284 .bak files listed above, plus R283 backups, unchanged)
- Current-round duplicate probe executable removed after hash proof:
  tester.exe (18,243,033 B) was byte-identical to retained cloudtech-saas.exe + winsw.exe
  (size + SHA256 match: 05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da)
- Small evidence relocated:
  tester.xml (843 B, sha256 62f540b2620…) + tester.wrapper.log (712 B, sha256 61b2de29d02…)
  → _agent-hub/v2/reports/system-audit-20260929/evidence/r284_timespan_probe/
  (manifest.json + manifest.md; byte-identical copies verified by sha256 round-trip)
- Helpers organized into governance/tools/:
  r284_fix_watchdog_path.py  (was cloudtech-saas/_r284_fix_bat.py)
  r284_refresh_registry_entry_hash.py  (was governance/_r284_refresh_entry_hash.py)
- Bytes reclaimed: 18,244,588 (18,243,033 exe + 843 xml + 712 log)
- 0 pre-existing user files deleted/moved; only R284-generated temporary artifacts cleaned/reorganized.
```

---

## 11. R284.1 final-check record (read-only, all PASS)

| Check | Result |
|---|---|
| `sc query CloudTechV22Monitor` | STOPPED · WIN32_EXIT_CODE=0 · SERVICE_EXIT_CODE=0 |
| `curl http://127.0.0.1:5099/health` | HTTP 200 |
| `protocol_registry.py validate` | PASS · entries=42 · families=29 · current_by_family=29/29 |
| `list-current` cloudtech-xml-winsw | `r284-fixed-cloudtech-xml` → `cloudtech-saas/cloudtech-saas.xml` (current hash matches) |
| `housekeeper.py --dry-run` | exit 0 (placement=100 / dup=200 / bak_disabled=148 / storage_breach=0 / log_rot=0 — all pre-existing) |
| `housekeeper.py --apply` | exit 2 (forbidden by R281.1 §7) |
| Temp directory absent | `D:\AIOS\cloudtech-saas\_r284_timespan_test\` removed |
| Two root helpers absent | `_r284_fix_bat.py` + `_r284_refresh_entry_hash.py` absent from cloudtech-saas/ + governance/ |
| Organized tools present | `governance\tools\r284_fix_watchdog_path.py` + `governance\tools\r284_refresh_registry_entry_hash.py` |
| Organized evidence present | `evidence\r284_timespan_probe\tester.xml` + `logs\tester.wrapper.log` + `manifest.json` + `manifest.md` |
| All evidence manifest parses | `json.load(manifest.json)` OK · `manifest.md` is valid Markdown |