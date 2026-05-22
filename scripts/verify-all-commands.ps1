# Verify all nextbrowser CLI commands - reports pass/fail per command
$ErrorActionPreference = "Continue"
$PY = Join-Path (Join-Path $PSScriptRoot "..") ".venv\Scripts\python.exe"
$CLI = @($PY, "-m", "nextbrowser_harness.cli")
Set-Location (Join-Path $PSScriptRoot "..")

$env:NEXTBROWSER_USE_CASE = "scrape"
$env:NEXTBROWSER_BROWSER = "native"
$env:NEXTBROWSER_AUTOMATION = "playwright"
$env:NEXTBROWSER_PROXY = "custom"

$results = @()

function Test-Cli {
    param([string]$Name, [string[]]$Args, [int]$Expect = 0)
    & $PY -m nextbrowser_harness.cli @Args 2>&1 | Out-Null
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $ok = ($code -eq $Expect)
    $script:results += [pscustomobject]@{ Command = $Name; Exit = $code; Expected = $Expect; OK = $ok }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host ("{0,-40} exit={1} (want {2})" -f $Name, $code, $Expect) -ForegroundColor $color
}

Write-Host "=== nextbrowser command verification ===" -ForegroundColor Cyan

Test-Cli "version" @("--version")
Test-Cli "init --env --yes" @("init", "--env", "--yes")
Test-Cli "status" @("status")
Test-Cli "tier lookup" @("tier", "lookup", "https://example.com")
Test-Cli "tier set" @("tier", "set", "test-verify.com", "2")
Test-Cli "scrape tier1" @("scrape", "https://httpbin.org/get", "--tier", "1", "--json")
Test-Cli "scrape tier2" @("scrape", "https://example.com", "--tier", "2", "--json")
Test-Cli "exec --js" @("exec", "https://example.com", "--js", "document.title", "--headless")
Test-Cli "browse headless" @("browse", "https://example.com", "--tier", "2", "--headless")
Test-Cli "account add" @("account", "add", "verify_cmd_01")
Test-Cli "account list" @("account", "list")
Test-Cli "account run" @("account", "run", "verify_cmd_01", "eval:document.title", "--url", "https://example.com")
Test-Cli "agent list-hosts" @("agent", "list-hosts")
Test-Cli "agent doctor" @("agent", "doctor")
Test-Cli "openclaw list-hosts" @("openclaw", "list-hosts")
Test-Cli "multilogin folders" @("multilogin", "folders")
Test-Cli "multilogin doctor" @("multilogin", "doctor") -Expect 1

if ($env:MULTILOGIN_FOLDER_ID) {
    Test-Cli "multilogin profiles" @("multilogin", "profiles", "--folder-id", $env:MULTILOGIN_FOLDER_ID)
} else {
    Write-Host "SKIP multilogin profiles (set MULTILOGIN_FOLDER_ID)" -ForegroundColor Yellow
}

Write-Host ""
$results | Format-Table -AutoSize
$bad = @($results | Where-Object { -not $_.OK }).Count
Write-Host "Result: $($results.Count - $bad)/$($results.Count) passed"
if ($bad -gt 0) { exit 1 }
exit 0
