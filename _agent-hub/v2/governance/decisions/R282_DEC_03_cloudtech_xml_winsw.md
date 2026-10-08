# R282 Decision Record · family=cloudtech-xml-winsw

| Field | Value |
|---|---|
| Decision ID | `r282-decision-cloudtech-xml-winsw` |
| Family | `cloudtech-xml-winsw` |
| Audit round | R282 (2026-09-29, post-R281.2 PROTOCOL_AUDIT) |
| Verdict | **DEFERRED REPAIR** — `.bak` XML is the only on-disk artifact; do NOT silently promote to live. Decision record + separate repair plan capture the path forward. |
| Confidence | HIGH for current disk state; repair requires user approval before apply |
| Captured at | 2026-09-29T14:43:00Z |

## 1. Question

The protocol family `cloudtech-xml-winsw` was UNRESOLVED because the canonical WinSW service descriptor `cloudtech-saas.xml` does NOT exist on disk — only a renamed copy `cloudtech-saas.xml.bak_C_1790215941` exists. Both `install.cmd` and `uninstall.cmd` reference the bare filename, so the WinSW-managed Windows service `CloudTechV22Monitor` CANNOT be installed out-of-the-box. What is the authoritative state, and what repair (if any) should this round propose?

## 2. Evidence (disk + live probe)

### 2.1 Files of record

| Path | Size (B) | mtime | sha256 (12) | Role |
|---|---:|---|---|---|
| `D:\AIOS\cloudtech-saas\install.cmd` | 1,124 | 2026-09-22 21:58 | n/a (text, sha256 not in registry for this size) | Windows batch installer |
| `D:\AIOS\cloudtech-saas\uninstall.cmd` | 394 | 2026-09-22 21:58 | n/a | Companion uninstaller |
| `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat` | 410 | 2026-09-24 10:15 | n/a | Direct-launch watchdog (Task Scheduler) |
| `D:\AIOS\cloudtech-saas\cloudtech-saas.xml.bak_C_1790215941` | 1,513 | 2026-09-24 10:12 | `509efc60c7d8` | WinSW service descriptor (RENAMED) |
| `D:\AIOS\cloudtech-saas\logs\` | 0 B dir | 2026-09-24 10:15 | n/a | EMPTY — install never wrote anything |

### 2.2 Install/uninstall failure mechanism (verbatim)

`install.cmd` line 19:
```cmd
winsw.exe install cloudtech-saas.xml
```
- `cloudtech-saas.xml` (without suffix) does NOT exist; the actual file is `cloudtech-saas.xml.bak_C_1790215941`.
- WinSW fails with `ERROR_FILE_NOT_FOUND` (Win32 2) on the descriptor arg.
- `goto :error` exits 1; service `CloudTechV22Monitor` is NOT installed.

`uninstall.cmd` lines 9, 12:
```cmd
winsw.exe stop cloudtech-saas.xml
winsw.exe uninstall cloudtech-saas.xml
```
- Same problem — bare `cloudtech-saas.xml` not found.

### 2.3 Service + V22 live state (recheck 2026-09-29 14:43)

| Check | Result | Verdict |
|---|---|---|
| `sc query CloudTechV22Monitor` | `OpenService 失败 1060: 指定的服务未安装` | service NOT installed (consistent with `install.cmd` being broken) |
| `netstat -ano` for `:5099` | `LISTENING` PID 23104 | V22 upstream IS alive |
| `GET http://127.0.0.1:5099/health` | HTTP 200 body `{"status":"ok","version":"22.0.0","service":"CloudTech V22 Unified Gateway","v10_modules_included":130}` | V22 healthy — adapter is OPTIONAL, V22 runs independently |

### 2.4 What the registry currently says

- One entry `cloudtech-xml-winsw` (`status=candidate`, path `cloudtech-saas/cloudtech-saas.xml.bak_C_1790215941`).
- `required_decision` text: "restore xml file or update install.cmd reference".
- `install.cmd` and `uninstall.cmd` are NOT yet in the registry (they are infrastructure, not protocol truth).

## 3. Decision

1. **The `.bak_C_1790215941` XML is NOT promoted to `current`.** Per the task instructions ("Do not silently promote a .bak file to a live deployed XML."), the renamed copy remains evidence-only — it documents that a working descriptor once existed, but the rename severed the live install path.
2. **`install.cmd` and `uninstall.cmd` are NOT promoted to `current` either** — they are broken (reference a non-existent file). Promoting them to `current` would be dishonest.
3. **The decision record IS the family pointer.** `current_by_family[cloudtech-xml-winsw]` is set to a new registry entry `r282-decision-cloudtech-xml-winsw` with `status=current`, pointing at this markdown.
4. **Legacy entry preserved**: the existing `cloudtech-xml-winsw` registry entry stays in `entries[]` with `status=superseded`, `superseded_by=r282-decision-cloudtech-xml-winsw`. The `.bak` XML stays on disk.
5. **Repair plan** (NOT applied in this round): see `reports/system-audit-20260929/CLOUDTECH_REPAIR_PLAN.md`. Two viable options are documented (rename `.bak` → `cloudtech-saas.xml`; OR edit `install.cmd` + `uninstall.cmd` to reference the `.bak` filename). Option selection + apply requires explicit user approval.
6. **Operational caveat**: V22 upstream is healthy (PID 23104, /health 200). The lack of a running `CloudTechV22Monitor` adapter is NOT a service outage for V22; the adapter is an optional watchdog. Repair can proceed without urgency.

## 4. Limitations

- This decision does NOT repair the install path. It documents the breakage and points at a separate repair plan with two options.
- No backup/snapshot of the `.bak` XML is taken in this round (the file is already a backup of an unverified pre-rename original). The repair plan proposes a dry-run rename + WinSW syntax validation before any install attempt.
- Encoding concern in `start_v22_watchdog.bat` header (GBK/UTF-8 mojibake in the `REM` comments) is documented in the repair plan but is cosmetic — the script runs because the actual command line is plain ASCII.

## 5. Superseded candidates

- `cloudtech-xml-winsw` registry entry → `status=superseded` (was `candidate`); `superseded_by=r282-decision-cloudtech-xml-winsw`.
- No other candidates exist for this family.

## 6. Verification timestamp

- File tree + sha256: 2026-09-29T14:43:00Z.
- Live probe (V22 health, service status, port scan): 2026-09-29T14:43:00Z.

## 8. R283 Addendum · File repair APPLIED, service INSTALLED (state STOPPED) · 2026-09-29T19:57:00Z

| Field | Value |
|---|---|
| Round | R283 (post-R282) |
| Outcome | **FILE_REPAIR_APPLIED_SERVICE_INSTALLED_START_BLOCKED** |
| User authorization | "全部执行掉" (R283 explicit apply approval after R282 plan review) |
| Scope | `D:\AIOS\cloudtech-saas\` ONLY + `D:\AIOS\_agent-hub\v2\governance\` + `D:\AIOS\_agent-hub\v2\reports\system-audit-20260929\` |

### 8.1 What was executed (chronological evidence)

1. **Backup created**: `cloudtech-saas.xml.pre_repair_R283_20260929T195700.bak` (1513 B, sha256 `509efc60c7d8...`, byte-identical to source `.bak_C_1790215941`).
2. **Atomic copy + rename**: `cloudtech-saas.xml.bak_C_1790215941` → `cloudtech-saas.xml` (via `cp -p` preserving mtime; original `.bak` NOT deleted).
3. **Capability registry backup**: `_aios_capability_registry_v2.py.bak_R283_pre_check_20260929T195700` (4657 B, sha256 `b46d5d6e42e8...`, byte-identical) — created BEFORE any `--check` because `register_to_aios()` is a mutating function.
4. **winsw.exe staged**: copied from `D:\AIOS\daemons_v2\winsw\winsw.exe` (sha256 `05b82d46ad33...`, 18,243,033 B) to `D:\AIOS\cloudtech-saas\cloudtech-saas.exe` (WinSW v3 alpha-10 requires binary-name to match descriptor). `winsw.exe` was already present locally — NO download performed.
5. **Service installed**: `sc qc CloudTechV22Monitor` shows:
   - `START_TYPE: 3 DEMAND_START` (= Manual startmode, matches XML)
   - `BINARY_PATH_NAME: "D:\AIOS\cloudtech-saas\cloudtech-saas.exe"`
   - `DISPLAY_NAME: CloudTech V22 Health Monitor (AIOS Bridge R156g)`
   - `STATE: 1 STOPPED` (Manual startmode respected; not auto-started)
   - `SERVICE_START_NAME: LocalSystem`
6. **Health probe**: `curl http://127.0.0.1:5099/health` → HTTP 200, body unchanged (`{"status":"ok","version":"22.0.0", "v10_modules_included":135}`).
7. **Registry governance promoted**: new entry `r283-canonical-cloudtech-xml` (status=current) pointing at `cloudtech-saas/cloudtech-saas.xml`. `r282-decision-cloudtech-xml-winsw` and `cloudtech-xml-winsw` both marked `superseded`. `protocol_registry.py validate` → PASS, 41 entries / 29 families / 29-29 currents resolved.

### 8.2 Verified unchanged artifacts (script hashes preserved)

| Artifact | sha256 (12) | Size | mtime |
|---|---|---:|---|
| `cloudtech-saas/install.cmd` | `d79c778d876d` | 1124 B | 2026-09-22 21:58 |
| `cloudtech-saas/uninstall.cmd` | `fb2b4c14129e` | 394 B | 2026-09-22 21:58 |
| `cloudtech-saas/start_v22_watchdog.bat` | `5a40784c8efe` | 410 B | 2026-09-24 10:15 |
| `_workzone/src/_aios_cloudtech_bridge.py` | `2c873cb7f325` | 15037 B | 2026-09-26 11:58 |
| `_workzone/src/_aios_capability_registry_v2.py` | `b46d5d6e42e8` | 4657 B | 2026-09-24 13:34 |

### 8.3 Known limitations (NOT in scope of Option A)

1. **`<resetfailure After="2 hour"/>` TimeSpan format**: WinSW v3 alpha-10 rejected this with `FormatException` AFTER successfully registering the service with the Service Control Manager. The service IS installed but WinSW's runtime start will fail on this same line if the user attempts `sc start CloudTechV22Monitor`. **Fix would require editing the XML** (Option A scope explicitly forbids XML edits beyond the rename; full descriptor fix is a separate R284+ task).
2. **`D:\AIOS\_venv312\Scripts\python.exe` does not exist** — the `_venv312` directory is missing entirely. Even if the TimeSpan format were fixed, `sc start` would fail with Win32 error 2 (file not found) when WinSW tries to spawn the Python interpreter. The bridge module is still importable via system Python 3.13.14 (smoke test passed) but the service's `binPath` is hardcoded to the missing venv path. **This is a SEPARATE infrastructure gap, not a cloudtech-saas repair gap.**
3. **install.cmd / uninstall.cmd not updated**: per Option A scope. They reference `winsw.exe install cloudtech-saas.xml` which works in WinSW v2.x but requires binary-name-matching in v3. R283 bypassed this by invoking `cloudtech-saas.exe install` directly. The scripts are functionally a paper trail to the v2.x era but are NOT executed by R283.
4. **Daily memory append SKIPPED**: `D:\AIOS\_agent-hub\memory\2026-09-29.md` does NOT exist. Per user instruction "do NOT recreate it if absent" — this is recorded here in the decision addendum instead.

### 8.4 Rollback status

Rollback is one-step trivial:
```cmd
"D:\AIOS\cloudtech-saas\cloudtech-saas.exe" uninstall
:: Then either delete cloudtech-saas.xml or rename it back to .bak_C_1790215941
```
The original `.bak_C_1790215941` file is preserved on disk, the R283 timestamped backup is preserved, and the capability-registry backup is preserved. No information loss; full disk state is recoverable.

### 8.5 References

- `cloudtech-saas/cloudtech-saas.xml` — canonical restored descriptor (current).
- `cloudtech-saas/cloudtech-saas.xml.bak_C_1790215941` — preserved rename artifact (audit history).
- `cloudtech-saas/cloudtech-saas.xml.pre_repair_R283_20260929T195700.bak` — R283 timestamped pre-rename snapshot.
- `_workzone/src/_aios_capability_registry_v2.py.bak_R283_pre_check_20260929T195700` — R283 pre-check safety backup.
- `reports/system-audit-20260929/CLOUDTECH_REPAIR_PLAN.md` — source plan, status updated to APPLIED.
- `reports/system-audit-20260929/R283_CLOUDTECH_EXECUTION_REPORT.md` — full phase-by-phase evidence report.
- `_workzone/logs/cloudtech_bridge.log` — NOT inspected (would require service start; skipped per Manual startmode).

## 7. References

- `cloudtech-saas/cloudtech-saas.xml.bak_C_1790215941` — the only WinSW descriptor on disk (registry entry now `superseded`).
- `cloudtech-saas/install.cmd` — installer (broken; line 19).
- `cloudtech-saas/uninstall.cmd` — uninstaller (broken; lines 9, 12).
- `cloudtech-saas/start_v22_watchdog.bat` — direct-launch watchdog (cosmetic encoding mojibake; functional).
- `reports/system-audit-20260929/CLOUDTECH_REPAIR_PLAN.md` — proposed repair (NOT applied).
- `reports/system-audit-20260929/CLOUDTECH_PROJECT_MAP.md` — full project map (R281.2).
- `_workzone/src/_aios_cloudtech_bridge.py` — out-of-tree Python adapter the service would host.
- `_workzone/src/_aios_capability_registry_v2.py` — capability registry the adapter self-registers into.
