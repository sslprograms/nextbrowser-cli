# Reddit + Multilogin X smoke test (Windows)
# Prerequisites: MLX app running, MULTILOGIN_* env set — see docs below
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Repo
$PY = ".\.venv\Scripts\python.exe"

Write-Host "=== Multilogin preflight ==="
& $PY -m nextbrowser_harness.cli multilogin doctor
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "MLX not ready. Required:"
    Write-Host "  1. Multilogin X desktop app running (launcher on :45001)"
    Write-Host "  2. MULTILOGIN_EMAIL + MULTILOGIN_PASSWORD  OR  MULTILOGIN_AUTOMATION_TOKEN"
    Write-Host "  3. MULTILOGIN_FOLDER_ID + MULTILOGIN_PROFILE_ID"
    Write-Host ""
    Write-Host "Setup:"
    Write-Host "  .\scripts\setup-multilogin.ps1"
    Write-Host "  # or manually:"
    Write-Host "  nextbrowser multilogin signin"
    Write-Host "  nextbrowser multilogin automation-token"
    Write-Host "  nextbrowser multilogin folders"
    exit 1
}

$env:NEXTBROWSER_BROWSER = "multilogin"
& $PY -m nextbrowser_harness.cli init --env

$shot = Join-Path $env:TEMP "nb-reddit-mlx.png"
Write-Host "=== Reddit browse via MLX profile ==="
& $PY -m nextbrowser_harness.cli browse "https://www.reddit.com" --browser multilogin --tier 3 --profile reddit_default --screenshot $shot
exit $LASTEXITCODE
