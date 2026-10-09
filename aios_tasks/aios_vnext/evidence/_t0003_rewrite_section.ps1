$path = "D:\AIOS\aios_tasks\aios_vnext\evidence\T0003_20261008-110409.md"
$content = Get-Content -LiteralPath $path -Raw -Encoding UTF8

$startMarker = "## 9. File index"
$endMarker = "## 10. Final verification"

$startIdx = $content.IndexOf($startMarker)
$endIdx = $content.IndexOf($endMarker)

if ($startIdx -lt 0 -or $endIdx -lt 0 -or $endIdx -le $startIdx) {
    Write-Output "ERROR: markers not found"
    exit 1
}

$newSection = @"
## 9. File index (this evidence)

```
D:\AIOS\aios_tasks\aios_vnext\evidence\
  T0003_20261008-110409.md                               - this file
  T0003_Overnight_Daily_Continue_fixed.xml               - input for schtasks /create
  T0003_Overnight_Daily_Continue_after.xml               - output of schtasks /query /xml (post-fix)
  T0003_xml_diff_1.txt                                   - before/after XML diff
  T0003_launcher_diff.txt                                - launcher diff (stale branch only)
  T0003_stale_test_output.txt                            - stale rejection test log
  T0003_final_test_stdout.txt                            - final clean re-run stdout (FINAL_EXIT=42)
  T0003_final_test_stderr.txt                            - final clean re-run stderr (empty)
  T0003_20261008-110409_apply_stale_patch.ps1            - auxiliary patch script
  T0003_20261008-110409_make_launcher_diff.ps1           - auxiliary diff script
  T0003_20261008-110409_update_index.ps1                 - auxiliary INDEX updater
  T0003_20261008-110409_final_stale_test.ps1             - final clean test runner
  preflight_T0003_20261008-110409.txt                    - preflight v4 (initial)
  preflight_T0003_postfix_20261008-110409.txt            - preflight v4 (after launcher patch)
  preflight_T0003_final_v2_20261008-110409.txt           - preflight v4 (final)

D:\AIOS\_backups\
  task-t0003-schtask-Overnight-20261008-110409.xml       - pre-fix scheduled task XML
  start-cc-current.ps1.pre-t0003-20261008-110409.bak     - pre-modification launcher
```


"@

$before = $content.Substring(0, $startIdx)
$after = $content.Substring($endIdx)
$newContent = $before + $newSection + $after
[System.IO.File]::WriteAllText($path, $newContent, [System.Text.UTF8Encoding]::new($false))
Write-Output "OK"
