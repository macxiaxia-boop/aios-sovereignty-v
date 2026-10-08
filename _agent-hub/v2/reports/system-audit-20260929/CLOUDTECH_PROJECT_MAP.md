# CloudTech Project Map — 2026-09-29

> Source-of-truth scope: `D:\AIOS\cloudtech-saas\` plus immediate out-of-tree dependencies.
> This map is for a NEW agent onboarding to the CloudTech-V22 health-monitor subsystem.

## 1. One-paragraph project summary

CloudTech SaaS in this workspace is a **thin WinSW-managed Windows service wrapper** around the
CloudTech V22 Unified Gateway. The wrapper does NOT contain application logic — it just registers
a Windows service named `CloudTechV22Monitor`, runs `python -m src._aios_cloudtech_bridge --check`
on each service start, and lets the upstream V22 process (PID 8544) keep serving on
`127.0.0.1:5099/health`. The actual Python bridge code lives in `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py`,
which is OUTSIDE this directory's tree.

## 2. Tech stack

| Layer | Choice |
|---|---|
| Service host | WinSW x64 v3.0.0-alpha.10 (downloaded on demand by install.cmd) |
| Encoding | CP65001 (UTF-8) at console; files saved with mixed GBK/UTF-8 historically |
| Monitored target | CloudTech V22 Unified Gateway @ `127.0.0.1:5099` |
| Python runtime | `D:\AIOS\_venv312\Scripts\python.exe` (Python 3.12 venv, **hardcoded**) |
| Python wrapper | `D:\AIOS\_venv312\Scripts\pythonw.exe` for direct-launch watchdog |
| Workdir | `D:\AIOS\_workzone` (hardcoded in service XML + .bat) |
| Log rotation | WinSW roll-by-size, threshold 10240 B, keep 5 files |

## 3. Git state

- Is a git repo: **NO** — no `.git/` directory inside `D:\AIOS\cloudtech-saas\`
- The harness environment flag `Is a git repository: true` is inherited from `D:\AIOS\` parent
- branch: N/A
- dirty files: N/A
- last commits: N/A

## 4. Tree (depth 5)

```
D:\AIOS\cloudtech-saas\
├── cloudtech-saas.xml.bak_C_1790215941   1,513 B   2026-09-24 10:12   WinSW service descriptor (RENAMED — install.cmd broken)
├── install.cmd                           1,124 B   2026-09-22 21:58   Windows batch installer
├── start_v22_watchdog.bat                  410 B   2026-09-24 10:15   Direct-launch watchdog (bypasses WinSW service)
├── uninstall.cmd                           394 B   2026-09-22 21:58   Companion uninstaller
└── logs\                                     0 B   2026-09-24 10:15   EMPTY — install never wrote anything
```

Total payload: **3,441 bytes (~3.4 KB)** across 4 files + 1 empty logs dir.

## 5. Entry points

| File | Role | Notes |
|---|---|---|
| `install.cmd` | Installs `CloudTechV22Monitor` as WinSW-managed Windows service in **Manual** mode | Downloads `winsw.exe` if missing, runs `winsw.exe install cloudtech-saas.xml`, then `curl http://127.0.0.1:5099/health` to verify V22 alive. **Broken out-of-box** — see §9. |
| `uninstall.cmd` | Stops + uninstalls the service | Does NOT touch V22 PID 8544 |
| `start_v22_watchdog.bat` | Direct-launch watchdog for Task Scheduler | Bypasses WinSW, runs `pythonw.exe -m src._aios_cloudtech_bridge --watch --watch-interval 300` with output → `logs/watchdog_stdout.log` |
| `cloudtech-saas.xml.bak_C_1790215941` | WinSW service descriptor | Service id `CloudTechV22Monitor`, executable `_venv312\Scripts\python.exe`, args `-m src._aios_cloudtech_bridge --check`, working dir `_workzone`, two-stage restart 30s/60s with 2h reset window, env `PYTHONUNBUFFERED=1` + `PYTHONIOENCODING=utf-8` |

## 6. Real bridge code (out of tree)

- `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` — actual Python module
- `D:\AIOS\_workzone\src\` — additional source modules (size 500MB total workzone dir; bridge is small)

## 7. Tests

**None** in `D:\AIOS\cloudtech-saas\`. No `test/`, `tests/`, `*_test.*` files. Verification is by
manual `curl http://127.0.0.1:5099/health` after install.

## 8. Build artifacts

**None** — no `dist/`, `build/`, `node_modules/`, `.next/`, `target/`, `__pycache__/` (at this depth).

## 9. Documentation

**None** — no README, no CHANGELOG, no docs/. Inline `REM` comments + XML `<description>` only.

## 10. Install / uninstall / direct-launch behavior

- **install.cmd**: 38-line batch. Downloads WinSW x64 v3.0.0-alpha.10 from GitHub releases, ensures `logs\` exists, calls `winsw.exe install cloudtech-saas.xml` (does NOT start), then curls V22 health. **Will fail** because `cloudtech-saas.xml` (without `.bak_C_*`) does not exist.
- **uninstall.cmd**: 19-line batch. `winsw.exe stop cloudtech-saas.xml` then `winsw.exe uninstall cloudtech-saas.xml`. Exits non-zero on failure. Does NOT clean `logs/` or `winsw.exe`.
- **start_v22_watchdog.bat**: 8-line batch. `chcp 65001`, `cd /d D:\AIOS\_workzone`, then `pythonw.exe -m src._aios_cloudtech_bridge --watch --watch-interval 300` with `>> logs/watchdog_stdout.log 2>&1`. Designed for Task Scheduler (no console).

## 11. Risks for new agent

1. **install.cmd is broken out-of-box** — references `cloudtech-saas.xml` (missing) instead of `cloudtech-saas.xml.bak_C_1790215941`. Two possible fixes: restore original name OR update install.cmd reference. Decision required.
2. **`logs/` is empty** — no `watchdog_stdout.log` ever written; suggests neither the service nor the direct launcher has run since install. Or logs were cleared.
3. **Hardcoded paths** — `D:\AIOS\_venv312\`, `D:\AIOS\_workzone\`, `D:\AIOS\cloudtech-saas\logs\watchdog_stdout.log` are all baked in. Moving any of these silently breaks service + watchdog.
4. **All real code lives outside scope** — onboarding work that touches Python logic must traverse `D:\AIOS\_workzone\`.
5. **No `.git/` here** — the project's git history, if any, lives in a parent repo.
6. **Encoding mojibake in `start_v22_watchdog.bat`** — header comment shows garbled GBK/UTF-8 mix; runs fine but cosmetic defect.
7. **V22 upstream is assumed running** — `127.0.0.1:5099/health` failure is logged but not recovered.
8. **WinSW alpha** — v3.0.0-alpha.10 is pinned; not production-stable.
9. **Service is `Manual`** — auto-start disabled by design.
10. **No test coverage** — only inline `curl` health check.

## 12. Quick orientation commands (for new agent)

```bash
# See what's actually in this directory
ls -la D:/AIOS/cloudtech-saas/

# Check V22 health
curl http://127.0.0.1:5099/health

# Verify workzone bridge exists
ls D:/AIOS/_workzone/src/_aios_cloudtech_bridge.py

# Verify python runtime
D:/AIOS/_venv312/Scripts/python.exe --version

# (DO NOT RUN) Test install.cmd to see why it fails
# powershell -File D:/AIOS/cloudtech-saas/install.cmd
```
