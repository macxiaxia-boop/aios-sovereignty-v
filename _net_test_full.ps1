# R325 Network Full Closure Test - 6 Categories
# UTF-8 with BOM required for PowerShell to parse Chinese strings
$PROXY = "http://127.0.0.1:7897"

function Test-URL {
    param([string]$url, [string]$cat, [int]$timeout=8)
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $r = Invoke-WebRequest -Uri $url -Proxy $PROXY -UseBasicParsing -TimeoutSec $timeout -MaximumRedirection 5
        $sw.Stop()
        $t = [Math]::Round($sw.Elapsed.TotalSeconds, 2)
        return "$cat | HTTP=$($r.StatusCode) TIME=${t}s | OK"
    } catch {
        return "$cat | FAIL | $($_.Exception.Message)"
    }
}

function Test-URL-NoProxy {
    param([string]$url, [string]$cat, [int]$timeout=8)
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout -MaximumRedirection 5
        return "$cat | HTTP=$($r.StatusCode) (TUN OK)"
    } catch {
        return "$cat | FAIL | $($_.Exception.Message)"
    }
}

function Test-DNSLeak {
    try {
        $r = Invoke-WebRequest -Uri "https://ipleak.net/json/" -UseBasicParsing -TimeoutSec 10
        $j = $r.Content | ConvertFrom-Json
        return "DNS=$($j.country_name) IP=$($j.ip)"
    } catch {
        return "DNS-FAIL"
    }
}

Write-Output "=== R325 Network Full Closure Test - 6 Categories ==="
Write-Output "Proxy: $PROXY"
Write-Output ""

Write-Output "[1] HTTP/HTTPS coverage via proxy 7897"
$tests = @(
    @{u="https://www.google.com"; c="Google"; t=8},
    @{u="https://github.com"; c="GitHub"; t=8},
    @{u="https://anthropic.com"; c="Anthropic"; t=8},
    @{u="https://www.youtube.com"; c="YouTube"; t=10},
    @{u="https://api.openai.com/v1/models"; c="OpenAI-API"; t=10},
    @{u="https://www.baidu.com"; c="Baidu-DIRECT"; t=5},
    @{u="https://www.qq.com"; c="QQ-DIRECT"; t=5},
    @{u="https://www.taobao.com"; c="Taobao-DIRECT"; t=5},
    @{u="https://www.douyin.com"; c="Douyin-DIRECT"; t=5}
)
foreach ($t in $tests) { Write-Output (Test-URL $t.u $t.c $t.t) }
Write-Output ""

Write-Output "[2] TUN mode coverage - foreign sites without explicit proxy"
$wout = @(
    @{u="https://www.google.com"; c="Google-TUN"; t=8},
    @{u="https://api.openai.com/v1/models"; c="OpenAI-TUN"; t=10}
)
foreach ($t in $wout) { Write-Output (Test-URL-NoProxy $t.u $t.c $t.t) }
Write-Output ""

Write-Output "[3] DNS leak test - ipleak.net"
Write-Output (Test-DNSLeak)
Write-Output ""

Write-Output "[4] Stability - 10x google"
$succ = 0; $total = 10; $times = @()
for ($i=1; $i -le $total; $i++) {
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $r = Invoke-WebRequest -Uri "https://www.google.com" -Proxy $PROXY -UseBasicParsing -TimeoutSec 8 -MaximumRedirection 3
        $sw.Stop()
        if ($r.StatusCode -eq 200) { $succ++ }
        $times += $sw.ElapsedMilliseconds
    } catch {}
}
$avg = if ($times.Count -gt 0) { [Math]::Round(($times | Measure-Object -Average).Average, 0) } else { 0 }
$max = if ($times.Count -gt 0) { ($times | Measure-Object -Maximum).Maximum } else { 0 }
$min = if ($times.Count -gt 0) { ($times | Measure-Object -Minimum).Minimum } else { 0 }
Write-Output "google x10: success=$succ/$total avg=${avg}ms min=${min}ms max=${max}ms"
Write-Output ""

Write-Output "[5] System network status"
$listen = netstat -ano | findstr ":7897.*LISTENING"
Write-Output "7897: $listen"
Write-Output "clash procs:"
Get-Process clash-verge,verge-mihomo -ErrorAction SilentlyContinue | Format-Table Name,Id,WorkingSet -AutoSize | Out-String | Write-Output
Write-Output "Wintun adapter:"
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Wintun|Meta|Tap" } | Format-Table Name,Status,InterfaceDescription,ifIndex -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "=== R325 Test Complete ==="