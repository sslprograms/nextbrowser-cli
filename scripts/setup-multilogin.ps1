# Multilogin X (MLX) setup for Nextbrowser Harness — Windows PowerShell
# Interactive: sign in, fetch automation token, pick folder/profile, write .env
#
# Usage:
#   .\scripts\setup-multilogin.ps1
#   .\scripts\setup-multilogin.ps1 -EnvFile .env -ProfileKey reddit_default
#   .\scripts\setup-multilogin.ps1 -SkipSignin   # token already in ~/.nextbrowser/multilogin_tokens.yaml
#
# Prerequisites: Multilogin X desktop app installed (https://multilogin.com)
$ErrorActionPreference = "Stop"

param(
    [string]$EnvFile = ".env",
    [string]$ProfileKey = "reddit_default",
    [switch]$SkipSignin,
    [switch]$NonInteractive
)

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot
$EnvPath = Join-Path $RepoRoot $EnvFile

function Write-Step([string]$Msg) { Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Invoke-Nextbrowser {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & $script:PY -m nextbrowser_harness.cli @Args
    if ($LASTEXITCODE -ne 0) { throw "nextbrowser failed: $($Args -join ' ')" }
}

function Update-DotEnv {
    param([string]$Path, [hashtable]$Vars)
    $newLines = [System.Collections.Generic.List[string]]::new()
    $updated = @{}
    if (Test-Path $Path) {
        foreach ($line in Get-Content $Path -Encoding UTF8) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') {
                $key = $matches[1]
                if ($Vars.ContainsKey($key)) {
                    $newLines.Add("$key=$($Vars[$key])")
                    $updated[$key] = $true
                    continue
                }
            }
            $newLines.Add($line)
        }
    }
    foreach ($k in $Vars.Keys) {
        if (-not $updated[$k]) { $newLines.Add("$k=$($Vars[$k])") }
    }
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $newLines | Set-Content -Path $Path -Encoding UTF8
}

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    foreach ($line in Get-Content $Path -Encoding UTF8) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$' -and -not $line.TrimStart().StartsWith("#")) {
            $name = $matches[1]
            $val = $matches[2].Trim().Trim('"').Trim("'")
            if (-not [string]::IsNullOrWhiteSpace($val)) {
                Set-Item -Path "Env:$name" -Value $val
            }
        }
    }
}

function Start-MlxDesktopApp {
    $exe = "$env:LOCALAPPDATA\Multilogin X App\MLXDesktopApp.exe"
    if (-not (Test-Path $exe)) {
        Write-Host "MLX desktop app not found at:`n  $exe" -ForegroundColor Yellow
        Write-Host "Install Multilogin X, then run this script again."
        return $false
    }
    if (-not (Get-Process -Name "MLXDesktopApp" -ErrorAction SilentlyContinue)) {
        Write-Host "Starting Multilogin X..."
        Start-Process $exe | Out-Null
        Start-Sleep -Seconds 8
    } else {
        Write-Host "Multilogin X is already running."
    }
    return $true
}

function Select-FromJsonList {
    param(
        [object[]]$Items,
        [string]$IdField = "id",
        [string]$NameField = "name",
        [string]$Prompt = "Select"
    )
    if (-not $Items -or $Items.Count -eq 0) {
        throw "No items returned from API."
    }
    for ($i = 0; $i -lt $Items.Count; $i++) {
        $item = $Items[$i]
        $id = $item.$IdField
        if (-not $id) { $id = $item.uuid }
        $name = $item.$NameField
        if (-not $name) { $name = $item.profile_name }
        if (-not $name) { $name = "(no name)" }
        Write-Host "  [$i] $name  ($id)"
    }
    if ($NonInteractive -and $Items.Count -eq 1) {
        $pick = $Items[0]
    } else {
        $idx = Read-Host "$Prompt [0-$($Items.Count - 1)]"
        $pick = $Items[[int]$idx]
    }
    $outId = $pick.$IdField
    if (-not $outId) { $outId = $pick.uuid }
    return $outId
}

Write-Host "Nextbrowser Harness — Multilogin X setup (Windows)"
Write-Host "Repo: $RepoRoot"

Write-Step "Python environment"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".venv\Scripts\Activate.ps1"
$script:PY = ".\.venv\Scripts\python.exe"
pip install -q -e .
pip install -q -e ".[playwright]"

Write-Step "Multilogin X desktop app"
Start-MlxDesktopApp | Out-Null

Write-Step "Load existing .env (if any)"
Import-DotEnv -Path $EnvPath

$hasToken = $env:MULTILOGIN_AUTOMATION_TOKEN -or $env:MULTILOGIN_TOKEN
if (-not $SkipSignin -and -not $hasToken) {
    Write-Step "MLX sign-in"
    if (-not $env:MULTILOGIN_EMAIL) {
        $env:MULTILOGIN_EMAIL = Read-Host "Multilogin X email"
    }
    if (-not $env:MULTILOGIN_PASSWORD) {
        $sec = Read-Host "Multilogin X password" -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        try {
            $env:MULTILOGIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
    Invoke-Nextbrowser multilogin signin
    Invoke-Nextbrowser multilogin automation-token
    # Do not write password to .env
} elseif ($SkipSignin) {
    Write-Host "Skipping sign-in (-SkipSignin). Using saved token or MULTILOGIN_AUTOMATION_TOKEN."
} else {
    Write-Host "Automation token already set in environment."
}

Write-Step "Choose workspace folder"
$folderId = $env:MULTILOGIN_FOLDER_ID
if (-not $folderId) {
    $foldersJson = & $PY -m nextbrowser_harness.cli multilogin folders
    if ($LASTEXITCODE -ne 0) { throw "multilogin folders failed" }
    $folders = $foldersJson | ConvertFrom-Json
    $folderId = Select-FromJsonList -Items @($folders) -Prompt "Folder"
}

Write-Step "Choose browser profile"
$profileId = $env:MULTILOGIN_PROFILE_ID
if (-not $profileId) {
    $env:MULTILOGIN_FOLDER_ID = $folderId
    $profilesJson = & $PY -m nextbrowser_harness.cli multilogin profiles --folder-id $folderId
    if ($LASTEXITCODE -ne 0) { throw "multilogin profiles failed" }
    $profiles = $profilesJson | ConvertFrom-Json
    $profileId = Select-FromJsonList -Items @($profiles) -IdField "id" -NameField "name" -Prompt "Profile"
}

Write-Step "Write $EnvFile and harness config"
$profileEnvKey = "MULTILOGIN_PROFILE_$($ProfileKey.ToUpper() -replace '[^A-Z0-9]', '_')"
$vars = @{
    NEXTBROWSER_BROWSER           = "multilogin"
    NEXTBROWSER_AUTOMATION        = "playwright"
    MULTILOGIN_FOLDER_ID          = $folderId
    MULTILOGIN_PROFILE_ID         = $profileId
    $profileEnvKey                = $profileId
}
if ($env:MULTILOGIN_EMAIL) {
    $vars["MULTILOGIN_EMAIL"] = $env:MULTILOGIN_EMAIL
}
Update-DotEnv -Path $EnvPath -Vars $vars
Import-DotEnv -Path $EnvPath

& $PY -m nextbrowser_harness.cli init --env
if ($LASTEXITCODE -ne 0) { throw "init --env failed" }

Write-Step "Doctor"
& $PY -m nextbrowser_harness.cli multilogin doctor
$doctorOk = ($LASTEXITCODE -eq 0)

Write-Host ""
Write-Host "Done. Saved to: $EnvPath" -ForegroundColor Green
Write-Host "  NEXTBROWSER_BROWSER=multilogin"
Write-Host "  MULTILOGIN_FOLDER_ID=$folderId"
Write-Host "  MULTILOGIN_PROFILE_ID=$profileId"
Write-Host "  $profileEnvKey=$profileId"
Write-Host ""
Write-Host "Test browse:"
Write-Host "  .\scripts\test-reddit-mlx.ps1"
Write-Host "Or:"
Write-Host "  nextbrowser exec `"https://www.reddit.com`" --browser multilogin --profile $ProfileKey --tier 3"
Write-Host ""
if (-not $doctorOk) {
    Write-Host "Doctor reported issues — ensure MLX app is running and launcher is reachable." -ForegroundColor Yellow
    exit 1
}
