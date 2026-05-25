# Multilogin X (MLX) setup for Nextbrowser Harness — Windows PowerShell
# Delegates to Python setup-wizard (single source of truth).
#
# Usage:
#   .\scripts\setup-multilogin.ps1
#   .\scripts\setup-multilogin.ps1 -EnvFile .env -ProfileKey reddit_default
#   .\scripts\setup-multilogin.ps1 -SkipSignin
#
# Prerequisites: Multilogin X desktop app (https://multilogin.com)
$ErrorActionPreference = "Stop"

param(
    [string]$EnvFile = ".env",
    [string]$ProfileKey = "reddit_default",
    [switch]$SkipSignin,
    [switch]$NonInteractive
)

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

Write-Host "Nextbrowser Harness — Multilogin X setup (Windows)"
Write-Host "Repo: $RepoRoot"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".venv\Scripts\Activate.ps1"
pip install -q -e .
pip install -q -e ".[playwright]"

$wizardArgs = @(
    "multilogin", "setup-wizard",
    "--env-file", $EnvFile,
    "--profile-key", $ProfileKey
)
if ($SkipSignin) { $wizardArgs += "--skip-signin" }
if ($NonInteractive) { $wizardArgs += "--non-interactive" }

& ".\.venv\Scripts\python.exe" -m nextbrowser_harness.cli @wizardArgs
exit $LASTEXITCODE
