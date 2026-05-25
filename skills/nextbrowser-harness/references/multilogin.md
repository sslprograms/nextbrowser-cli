# Multilogin X (MLX) — agent guide

## Rules for AI agents (read first)

1. **Never** edit `~/.nextbrowser/multilogin_tokens.yaml` with Python, `sed`, or patch scripts.
2. **Never** store Multilogin passwords in `.env`, yaml, or skill metadata — only email in `.env`.
3. **Always** run `nextbrowser multilogin setup-wizard` for MLX setup (or the platform script below).
4. **Always** run `nextbrowser multilogin doctor` before `exec --browser multilogin`; follow `next_steps` in JSON.
5. **`--profile reddit_default`** requires `MULTILOGIN_PROFILE_REDDIT_DEFAULT=<uuid>` (or use `--profile default` with only `MULTILOGIN_PROFILE_ID`).

## Guided setup (recommended)

```bash
nextbrowser multilogin setup-wizard
```

| OS | Script (delegates to setup-wizard) |
|----|---------|
| Windows | `.\scripts\setup-multilogin.ps1` |
| Linux / macOS | `chmod +x scripts/setup-multilogin.sh && ./scripts/setup-multilogin.sh` |

Or: `nextbrowser multilogin setup` (prints platform-specific hints).

## Start MLX desktop app

| OS | How |
|----|-----|
| Windows | `%LOCALAPPDATA%\Multilogin X App\MLXDesktopApp.exe` |
| macOS | `open -a "Multilogin X App"` or install from multilogin.com |
| Linux | App menu, or `MULTILOGIN_APP_EXE` (e.g. `/opt/mlx/desktop.bin`); headless: `sudo apt install xvfb` |

## Manual CLI flow

```bash
nextbrowser multilogin setup-wizard
nextbrowser multilogin doctor
```

Legacy steps (if wizard unavailable):

```bash
nextbrowser multilogin signin
nextbrowser multilogin automation-token
nextbrowser multilogin folders
nextbrowser multilogin profiles --folder-id <folder-uuid>
nextbrowser multilogin print-env
nextbrowser init --env
```

**macOS / Linux session env:**

```bash
export MULTILOGIN_EMAIL="you@example.com"
export MULTILOGIN_FOLDER_ID="<folder-uuid>"
export MULTILOGIN_PROFILE_ID="<profile-uuid>"
export MULTILOGIN_PROFILE_REDDIT_DEFAULT="<profile-uuid>"
export NEXTBROWSER_BROWSER=multilogin
export NEXTBROWSER_PROXY=none
```

**Windows session env:**

```powershell
$env:MULTILOGIN_EMAIL = "you@example.com"
$env:MULTILOGIN_FOLDER_ID = "<folder-uuid>"
$env:MULTILOGIN_PROFILE_ID = "<profile-uuid>"
$env:MULTILOGIN_PROFILE_REDDIT_DEFAULT = "<profile-uuid>"
$env:NEXTBROWSER_BROWSER = "multilogin"
$env:NEXTBROWSER_PROXY = "none"
```

## Run automation

```bash
nextbrowser exec "https://www.reddit.com" \
  --browser multilogin \
  --profile reddit_default \
  --tier 3 \
  --steps-file examples/steps-reddit.json
```

## Stop stuck profiles

```bash
nextbrowser multilogin stop-all
```

## API notes

- Signin MD5-hashes password (unless `MULTILOGIN_SIGNIN_PLAIN=1`)
- `automation-token` uses `expiration_period=24h` by default
- Tokens live in `~/.nextbrowser/multilogin_tokens.yaml` (managed by CLI only)
