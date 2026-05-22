# Full product smoke test - run from repo root
$ErrorActionPreference = "Continue"
$PY = Join-Path $PSScriptRoot ".." ".venv" "Scripts" "python.exe"
$Results = @()
$shotDir = Join-Path $env:TEMP "nb-product-test"
New-Item -ItemType Directory -Force -Path $shotDir | Out-Null

function Test-Cmd {
    param([string]$Name, [string[]]$Args, [int]$ExpectExit = 0)
    $outFile = Join-Path $shotDir "$($Name -replace '[^a-zA-Z0-9_-]','_').log"
    $errFile = "$outFile.err"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $PY -m nextbrowser_harness.cli @Args 2> $errFile | Tee-Object -FilePath $outFile
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    $sw.Stop()
    $ok = ($code -eq $ExpectExit)
    $sec = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    $script:Results += [pscustomobject]@{
        Feature = $Name; Exit = $code; Expected = $ExpectExit; OK = $ok; Sec = $sec; Log = $outFile
    }
    if (-not $ok) { Write-Host "FAIL: $Name exit=$code expected=$ExpectExit" -ForegroundColor Red }
    else { Write-Host "OK: $Name (${sec}s)" -ForegroundColor Green }
}

Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "=== Nextbrowser Harness full feature test ===" -ForegroundColor Cyan

& $PY -m pytest tests/ -q --tb=no 2>&1 | Tee-Object (Join-Path $shotDir "pytest.log")
$pytestOk = ($LASTEXITCODE -eq 0)
$Results += [pscustomobject]@{ Feature = "pytest"; Exit = $LASTEXITCODE; Expected = 0; OK = $pytestOk; Sec = 0; Log = (Join-Path $shotDir "pytest.log") }

$env:NEXTBROWSER_USE_CASE = "scrape"
$env:NEXTBROWSER_BROWSER = "native"
$env:NEXTBROWSER_PROXY = "custom"
$env:NEXTBROWSER_AUTOMATION = "playwright"

Test-Cmd "version" @("--version")
Test-Cmd "init-env" @("init", "--env", "--yes")
Test-Cmd "status" @("status")
Test-Cmd "tier-lookup-reddit" @("tier", "lookup", "https://www.reddit.com")
Test-Cmd "tier-set-example" @("tier", "set", "example.com", "2")
Test-Cmd "scrape-tier1" @("scrape", "https://httpbin.org/get", "--tier", "1", "--json")
Test-Cmd "scrape-tier2" @("scrape", "https://example.com", "--tier", "2", "--json")

$nativeShot = Join-Path $shotDir "browse-native.png"
Test-Cmd "browse-native-t3" @("browse", "https://www.reddit.com", "--browser", "native", "--tier", "3", "--screenshot", $nativeShot, "--headless")

Test-Cmd "account-add" @("account", "add", "test_smoke_01", "--notes", "product test")
Test-Cmd "account-list" @("account", "list")
Test-Cmd "agent-list-hosts" @("agent", "list-hosts")
Test-Cmd "agent-doctor" @("agent", "doctor")
Test-Cmd "mlx-folders" @("multilogin", "folders")

Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
$Results | Format-Table -AutoSize
$fail = @($Results | Where-Object { -not $_.OK }).Count
$pass = @($Results | Where-Object { $_.OK }).Count
Write-Host "Passed $pass of $($Results.Count). Logs: $shotDir"
if ($fail -gt 0) { exit 1 }
exit 0
