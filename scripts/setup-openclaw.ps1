# Install Nextbrowser Harness + OpenClaw skill (Windows)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

Write-Host "==> Nextbrowser Harness — OpenClaw setup (Windows)"
Write-Host "Repo: $RepoRoot"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".venv\Scripts\Activate.ps1"

pip install -e .
pip install -e ".[playwright]"
playwright install chromium

nextbrowser agent install --host all --force
nextbrowser agent doctor

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Configure env for your agent — see docs/AGENT_HOSTS.md and docs/OPENCLAW.md"
Write-Host "  2. nextbrowser init --env"
Write-Host "  3. Start a new OpenClaw session"
