$actual = (Get-FileHash -Algorithm SHA256 "D:\AIOS\_agent-hub\policy\model-policy.v1.yaml").Hash
$expected_line = (Select-String -Path "D:\AIOS\_agent-hub\policy\model-policy.v1.sha256" -Pattern "^sha256:" | Select-Object -First 1).Line
$expected = ($expected_line -split ":", 2)[1].Trim()
Write-Host "actual  = $actual"
Write-Host "expected= $expected"
if ($actual -eq $expected) {
    Write-Host "[OK] sha256 match"
    exit 0
} else {
    Write-Host "[FATAL] sha256 mismatch"
    exit 2
}