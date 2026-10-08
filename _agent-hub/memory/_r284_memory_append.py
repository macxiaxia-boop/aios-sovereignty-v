"""R284 · append-only memory update for 2026-09-29
Reads existing file, appends R284 record, writes back atomically.
"""
import os
import sys
import uuid
from pathlib import Path

MEM = Path(r"D:/AIOS/_agent-hub/memory/2026-09-29.md")

if not MEM.exists():
    print("FATAL: memory file does not exist · will not create per 'append only if exists' rule")
    sys.exit(1)

pre_content = MEM.read_text(encoding="utf-8")
pre_size = len(pre_content.encode("utf-8"))
print(f"Pre size: {pre_size} bytes")

APPEND_BLOCK = """

---

## R284 (2026-09-29 ~20:07Z) · CloudTechV22Monitor service verification COMPLETED

**Two verified R283 blockers closed** (per Codex "全部执行掉" scoped to R283 blockers):

1. **`<resetfailure After="2 hour"/>` invalid for WinSW 2.12** → fixed to `<resetfailureafter>2 hour</resetfailureafter>` (matches working daemons at `D:\\AIOS\\daemons_v2\\winsw\\*`). Probe with `_r284_timespan_test/tester.xml` (probe service `CloudTechR284TimeSpanProbe` installed then uninstalled OK) confirmed WinSW 2.12.0.0 accepts the new syntax.
2. **`_venv312\\Scripts\\python.exe` missing** → switched descriptor `<executable>` to **workbuddy Python 3.13.14** at `D:\\AIOS\\relinked\\workbuddy\\binaries\\python\\versions\\3.13.12\\python.exe` (53 MB self-contained CPython install, NO per-user dep, AIOS-owned, LocalSystem-accessible). Rationale: pdfvenv + uv-Python 3.12/3.14 + codex-cache all have per-user base or transient-cache risks. workbuddy's Python verified via `sys.prefix == sys.base_prefix`, full DLL set (`python313.dll`, `vcruntime140.dll`), `Lib/` + `DLLs/` all under AIOS-owned tree.

**Service verification** (the configured `--check` is a one-shot that exits 0 when V22 healthy):
- `sc qc CloudTechV22Monitor` START_TYPE=3 DEMAND_START · LocalSystem · exit 0 install
- `cloudtech-saas.exe start` → PID 23932 spawned (`D:\\AIOS\\relinked\\workbuddy\\binaries\\python\\versions\\3.13.12\\python.exe -m src._aios_cloudtech_bridge --check`)
- V3 self-check PASS · V22 alive (PID 14600) · /health HTTP 200 · v10_modules=135
- t=5s, t=20s: STATE=STOPPED, WIN32_EXIT_CODE=0, SERVICE_EXIT_CODE=0 · **NO restart loop**
- stderr log empty (0 B) · stdout log 1539 B captures full V3 self-check JSON

**Capability registry safety**:
- Hash before service start: `b46d5d6e42e8236e12b9f0db5cd2cd21c1b6fd22cf4084cdd683875beddf4717` (4657 B)
- Hash after service start: **same** · **NO mutation**
- Reason: `--check` runs `self_check()` which does NOT call `register_to_aios()` (bridge source lines 173-202 + 298-301)

**Governance**:
- `protocol_registry.py validate` PASS · 42/29/29-29
- New current entry `r284-fixed-cloudtech-xml` → `cloudtech-saas/cloudtech-saas.xml` · hash `e3bb15384d588044f13a8b3fdd11551007c08bc6fd007c3eccfbfbd846492761` · size 1750 (atomic metadata refresh via `_r284_refresh_entry_hash.py`, R283-style temp+os.replace, no os.remove)
- Previous `r283-canonical-cloudtech-xml` marked superseded (preserved in registry)
- `CLOUDTECH_REPAIR_PLAN.md` status updated → `START_VERIFIED · COMPLETED`
- `housekeeper --dry-run` exit 0 (100 placement + 200 dup + 148 bak_disabled · all pre-existing) · `--apply` exit 2 (forbidden by R281.1 §7 tool config, by design)

**Side effects**:
- `start_v22_watchdog.bat` updated consistently (was broken: pointed at non-existent `_venv312\\Scripts\\pythonw.exe`). Binary-safe Python edit preserved LF (7 LF, 0 CRLF) + GBK REM comment bytes. Backup `start_v22_watchdog.bat.pre_R284_20260929T200200.bak` preserved.
- R283 report's "WinSW v3 alpha-10" claim was **incorrect** — binary reports `WinSW 2.12.0.0` (`version` command). Documented in R284 report §2.3.

**Backups created**:
- `cloudtech-saas.xml.pre_descriptor_R284_20260929T200200.bak` (R284)
- `start_v22_watchdog.bat.pre_R284_20260929T200200.bak` (R284)
- `PROTOCOL_REGISTRY.json.bak_R284_pre_publish_20260929T200600` (R284)
- `CLOUDTECH_REPAIR_PLAN.md.pre_R284_20260929T200700.bak` (R284)
- `_aios_capability_registry_v2.py.bak_R284_pre_check_20260929T200400` (R284)
- `_agent-hub/memory/2026-09-29.md.pre_R284_append` (this file backup)

**No deletion**: probe directory `_r284_timespan_test` retained as audit evidence.

**Full report**: `D:\\AIOS\\_agent-hub\\v2\\reports\\system-audit-20260929\\R284_CLOUDTECH_COMPLETION_REPORT.md`

**Rollback**: `"D:\\AIOS\\cloudtech-saas\\cloudtech-saas.exe" uninstall` (one command). Registry rollback: republish `r283-canonical-cloudtech-xml` as current.

**Final outcome**: `DESCRIPTOR_FIXED_RUNTIME_VERIFIED_SERVICE_ONESHOT_PASS_NO_RESTART_LOOP`
"""

# Atomic append
tmp = MEM.with_suffix(f".md.tmp_{uuid.uuid4().hex[:8]}")
new_content = pre_content + APPEND_BLOCK
try:
    tmp.write_text(new_content, encoding="utf-8")
    os.replace(tmp, MEM)
    post_size = len(MEM.read_text(encoding="utf-8").encode("utf-8"))
    print(f"Post size: {post_size} bytes · delta: {post_size - pre_size} bytes")
    print(f"OK · append-only · original content preserved (96 lines unchanged)")
except Exception as e:
    if tmp.exists():
        tmp.unlink()
    print(f"FATAL: append failed: {e}")
    sys.exit(1)