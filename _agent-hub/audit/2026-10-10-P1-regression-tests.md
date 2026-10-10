# T2 regression-tests integration - 2026-10-10

## Status: DONE - 3/3 pytest PASSED in 0.34s

## Files created (added to existing _agent-hub/policy/regression-tests/)
```
D:\AIOS\_agent-hub\policy\regression-tests\verify_ext_d.py         COPY from _agent-hub/scripts/
D:\AIOS\_agent-hub\policy\regression-tests\discover_cloudtech.py  COPY from _agent-hub/scripts/
D:\AIOS\_agent-hub\policy\regression-tests\_yaml_sha_check.py       NEW (yaml vs manifest sha)
D:\AIOS\_agent-hub\policy\regression-tests\test_adapter_registry.py NEW (pytest wrapper, 3 tests)
D:\AIOS\_agent-hub\policy\regression-tests\run_all.py              NEW (unified entry)
```

## sha256 of new files
```
_yaml_sha_check.py     900 B  sha256=942159E7762721F80CC1B5DE71FABA934515E4D5CD9C9498B78EFCD2FBAD595E
test_adapter_registry.py  2175 B  sha256=94C598D12B267544C6E44BE7ED233CFB6D694743EC5CF45C0BA49244939B7F44
run_all.py            1185 B  sha256=F5A7306D5EFB0DD241116C1889FDFF5F32A8B9E6DFC5BA952D4887C2FEFE8EFE
```

## pytest result
```
$ python -m pytest D:\AIOS\_agent-hub\policy\regression-tests -v
test_adapter_registry.py::test_verify_ext_d_passes          PASSED
test_adapter_registry.py::test_discover_cloudtech_runs      PASSED
test_adapter_registry.py::test_yaml_sha_matches_manifest    PASSED
=== 3 passed in 0.28s ===
```

## run_all.py entry
```bash
$ python D:\AIOS\_agent-hub\policy\regression-tests\run_all.py
=== verify_ext_d ===
4/4 adapters OK
  [PASS]
=== discover_cloudtech ===
{...3 prefixes...}
  [PASS]
=== yaml sha manifest ===
yaml sha matches manifest
  [PASS]
=== SUMMARY ===
  verify_ext_d: PASS
  discover_cloudtech: PASS
  yaml sha manifest: PASS
ALL PASSED
```

## Notes
- _t1b_patch.py didn't exist (was a script I ran via python -c, didn't save to disk) — SKIP
- existing regression-tests already had regression_tests.py + README - preserved as-is
- Originals in _agent-hub/scripts/ kept (additive copy, not move)

## Red lines respected
- 没动 EX-001~010 byte
- 没 force push
- 没动 AIOSCentralCollector / aios_kernel

--- Codex supervisor - T2 regression tests DONE - 3/3 PASS - 2026-10-10
