$stdoutPath = 'D:\AIOS\aios_tasks\aios_vnext\evidence\T0003_final_test_stdout.txt'
$stderrPath = 'D:\AIOS\aios_tasks\aios_vnext\evidence\T0003_final_test_stderr.txt'
$proc = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','D:\demo\start-cc-current.ps1' -NoNewWindow -PassThru -Wait -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
Write-Output ('FINAL_EXIT=' + $proc.ExitCode)
Write-Output '--- STDOUT ---'
if (Test-Path $stdoutPath) { Get-Content $stdoutPath }
Write-Output '--- STDERR ---'
if (Test-Path $stderrPath) { Get-Content $stderrPath }
