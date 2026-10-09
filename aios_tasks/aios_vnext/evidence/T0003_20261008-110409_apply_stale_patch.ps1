$path = 'D:\demo\start-cc-current.ps1'
$content = Get-Content -LiteralPath $path -Raw -Encoding UTF8

$lf = [char]10
$oldBlock = "if (`$generatedAt -gt `$now.AddMinutes(5) -or `$expiresAt -le `$now -or (`$now - `$generatedAt).TotalHours -gt 12) {" + $lf +
           '    $staleMsg = "STALE_HANDOFF: generated=$generatedAt expires=$expiresAt now=$now"' + $lf +
           '    Write-Output $staleMsg' + $lf +
           '    Write-Error $staleMsg' + $lf +
           '    exit 42' + $lf +
           '}'

$newBlock = "if (`$generatedAt -gt `$now.AddMinutes(5) -or `$expiresAt -le `$now -or (`$now - `$generatedAt).TotalHours -gt 12) {" + $lf +
           '    $staleMsg = "STALE_HANDOFF: generated=$generatedAt expires=$expiresAt now=$now"' + $lf +
           '    Write-Output $staleMsg' + $lf +
           '    Write-Error -Message $staleMsg -ErrorAction SilentlyContinue' + $lf +
           '    exit 42' + $lf +
           '}'

if ($content.Contains($oldBlock)) {
    $newContent = $content.Replace($oldBlock, $newBlock)
    Set-Content -LiteralPath $path -Value $newContent -Encoding UTF8
    Write-Output "PATCHED: Write-Error now uses -ErrorAction SilentlyContinue to honor exit 42"
    Write-Output "OLD_LEN: $($content.Length)"
    Write-Output "NEW_LEN: $($newContent.Length)"
} else {
    Write-Output "NOT_FOUND: stale branch pattern not located"
    exit 1
}