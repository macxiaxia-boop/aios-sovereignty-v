# _archived — historical one-off scripts and logs

> **Status**: ARCHIVED (preserve-only, do NOT re-run)
> **Archived by**: Codex supervisor (2026-10-10 P1 cleanup)
> **Purpose**: hold one-off session scripts + ephemeral audit logs that are not part of the regression suite
> **Use**: For archaeology; if you need the same operation, write a NEW script and append manifest entry

## Manifest

### Python helpers (one-off session use)
| File | sha256 | size | Origin |
|------|--------|------|--------|
| _full_audit_ex.py | 65C4E3BE46BCA107... | 1838 B | EX-001~010 byte comparison helper |
| _recovery_t1.py | 88B0B9B996198862... | 5339 B | T1 yaml exception_rules indent fix |
| _recovery_t2.py | 6528B531A090DAF8... | 8702 B | T2 EXT-D 7-file recovery |
| _recovery_t2_run.py | 7D6C69EAA08A9FAE... | 2218 B | T2 subprocess runner |
| _t4_verify_ex.py | 8ED63C65D34B545E... | 1466 B | T4 EX-001~010 byte verifier |
| _test_v2.py | D27C01E603F11F0B... | 456 B | T3 yaml parse test |
| _regression_setup.py | 2C3CFF9D641FDE91... | 5425 B | P1 regression-tests setup |

### Test logs (post-batch run outputs)
| File | sha256 | size | Origin |
|------|--------|------|--------|
| _t1_pytest_run.log | 54D7194F2F4D1417... | 7095 B | T1 initial pytest failed run |
| _t1_r1348b_final.log | 7D43C7C3A37551A6... | 1619 B | T1 r1348b final 10/10 PASS log |
| _p0_critical_3.log | 2E513E0C48F99308... | 102 B | P0 critical 3 tests output |
| _p0_full_integration.log | 075C4FD1437EBD3F... | 275 B | P0 179 full integration PASS |

## Rules

1. **DO NOT** re-run these scripts — they may have hardcoded paths or assumptions from their session
2. **DO NOT** modify — only add new entries with manifest sha256
3. **Use canonical versions** instead:
   - For EX verification: `regression-tests/test_adapter_registry.py::test_yaml_sha_matches_manifest`
   - For adapter 4/4 OK: `scripts/verify_ext_d.py` or `regression-tests/run_all.py`
   - For CloudTech discovery: `scripts/discover_cloudtech.py`
4. **Backup policy**: archived files preserved indefinitely unless user explicitly deletes

## Provenance

These files were created during the 2026-10-10 P0 三件套 recovery batch + the prior T1-T6 batch earlier that day. They were moved here from `_agent-hub/scripts/` and `_agent-hub/audit/` when:

1. Direct user inspection no longer needs them (all production paths use canonical regression suite)
2. Disk cleanup was appropriate (7 helper scripts + 4 ephemeral logs = 33 KB freed from active paths)
3. History preservation was important (auditability of how P0 was achieved)

## Restore policy

If user ever needs to re-run any of these (e.g., to reproduce a test setup or a specific failure scenario):

```powershell
Copy-Item D:\AIOS\_agent-hub\policy\regression-tests\_archived\<file> <dest>
python <dest>
```

But again — most cases do NOT need this; the canonical regression suite covers the same surface.

--- Codex supervisor · _archived 维护 2026-10-10
