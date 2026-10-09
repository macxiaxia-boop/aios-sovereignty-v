#!/usr/bin/env python3
"""
不留尾巴 · 全量清旧 backup / staging · 2026-10-09
用户授权: 全部授权, 全部做掉, 不留尾巴
Codex 01a11c30 supervisor
"""
import os
from pathlib import Path

FILES_TO_DELETE = [
    # 自己的 staging
    r"D:\AIOS\_agent-hub\AGENTS.md.SOVEREIGNTY-H.appended",
    # 旧 audit (replaced by v2)
    r"D:\AIOS\_agent-hub\reports\sovereignty-v\acceptance_phase_i.py",
    r"D:\AIOS\_agent-hub\reports\sovereignty-v\acceptance_phase_i.log",
    # backup files (SANITIZED 但冗余)
    r"C:\Users\xinzh\.codex\run-bridge.py.disabled",
    r"C:\Users\xinzh\.codex\run-bridge.py.R2-fix.bak.2026-10-09",
    # 73MB cc-switch DB backup (rollback 不需要)
    r"C:\Users\xinzh\.cc-switch\cc-switch.db.bak.2026-10-09R2-fix",
    # v2 src bak (8 个, 父线程迭代 backup)
    r"D:\AIOS\_agent-hub\v2\src\claude_adapter.py.bak.20261008-223507",
    r"D:\AIOS\_agent-hub\v2\src\claude_adapter.py.bak.20261008-224130",
    r"D:\AIOS\_agent-hub\v2\src\probes.py.bak.20261008-221446",
    r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py.bak.20261008-221414",
    r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py.bak.20261008-222501",
    r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py.bak.20261008-223507",
    r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py.bak.audit-fix-20261009-091442",
    r"D:\AIOS\_agent-hub\v2\src\v2_consumer.py.bak.audit-fix2-20261009-091448",
    r"D:\AIOS\_agent-hub\v2\tests\test_p8_t15.py.bak.20261009-091709",
    # Codex sqlite bak (30 天)
    r"C:\Users\xinzh\.codex\..codex-global-state.json.bak.tmp-1790654972910-c99dc4e1-8f00-41a3-8837-9a9e2f351264",
    r"C:\Users\xinzh\.codex\logs_2.sqlite.bak.20260923-125804",
    r"C:\Users\xinzh\.codex\logs_2.sqlite.bak.20260924-094555",
    r"C:\Users\xinzh\.codex\state_5.sqlite.bak.20260923-125804",
    # hermes/openclaw bak
    r"D:\AIOS\_relinked\hermes\config.yaml.bak.20260927_144119",
    r"D:\AIOS\_relinked\hermes\backups\config\config.yaml.bak.2026-09-02",
    r"D:\AIOS\_relinked\hermes\hermes-agent\gateway\run.py.bak.2026-09-02",
    r"D:\AIOS\_relinked\openclaw\openclaw.json.bak.1",
    # relinked codex (4 个)
    r"D:\AIOS\_relinked\codex\..codex-global-state.json.bak.tmp-1790654972910-c99dc4e1-8f00-41a3-8837-9a9e2f351264",
    r"D:\AIOS\_relinked\codex\logs_2.sqlite.bak.20260923-125804",
    r"D:\AIOS\_relinked\codex\logs_2.sqlite.bak.20260924-094555",
    r"D:\AIOS\_relinked\codex\state_5.sqlite.bak.20260923-125804",
]

deleted, total_bytes, missing = [], 0, []
for f in FILES_TO_DELETE:
    p = Path(f)
    if p.exists():
        try:
            sz = p.stat().st_size
            p.unlink()
            deleted.append(f)
            total_bytes += sz
            print(f"  ✅ DEL {sz:>12,d}  {f}")
        except Exception as e:
            print(f"  ❌ FAIL {f}: {e}")
    else:
        missing.append(f)
        print(f"  ⏭️  N/A  {f}")

print(f"\n=== SUMMARY ===")
print(f"Deleted: {len(deleted)}")
print(f"Freed:   {total_bytes:,d} bytes = {total_bytes/1024/1024:.1f} MB")
print(f"Missing: {len(missing)}")