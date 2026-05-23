# Multilogin X (MLX)

## Prerequisites

1. Multilogin X desktop app installed and running
2. MLX account credentials (same as the desktop app)

Windows — start app if not running:

```powershell
$exe = "$env:LOCALAPPDATA\Multilogin X App\MLXDesktopApp.exe"
if (-not (Get-Process MLXDesktopApp -EA SilentlyContinue)) { Start-Process $exe }
```

## Bootstrap

```bash
nextbrowser multilogin signin
nextbrowser multilogin automation-token
nextbrowser multilogin folders
nextbrowser multilogin profiles --folder-id $MULTILOGIN_FOLDER_ID
nextbrowser multilogin doctor
```

Tokens are stored in `~/.nextbrowser/multilogin_tokens.yaml` (gitignored).

## Run automation on MLX profile

```bash
nextbrowser exec "https://www.reddit.com" \
  --browser multilogin \
  --profile reddit_default \
  --steps-file examples/steps-reddit.json
```

Map profile keys via env:

- `MULTILOGIN_PROFILE_REDDIT_DEFAULT=<profile-uuid>`
- or `MULTILOGIN_PROFILE_ID=<default-uuid>`

## Start / stop profiles

```bash
nextbrowser multilogin start <profile-uuid> --folder-id <folder-uuid>
nextbrowser multilogin stop-all
```

If `stop` returns 404 on the launcher, use `stop-all`.

## API notes

- Signin sends **MD5 hex** of the password (MLX API requirement)
- Automation token requires `expiration_period` query (e.g. `24h`)
