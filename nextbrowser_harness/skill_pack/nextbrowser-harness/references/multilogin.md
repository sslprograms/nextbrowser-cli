# Multilogin X (MLX) — agent guide

## Rules for AI agents (read first)

1. **Never** edit `~/.nextbrowser/multilogin_tokens.yaml` with Python, `sed`, or patch scripts.
2. **Never** delete `automation_token` from the token file to “force refresh” — run CLI commands instead.
3. **Setup script by OS:**
   - **Windows:** `.\scripts\setup-multilogin.ps1`
   - **Linux / macOS:** `./scripts/setup-multilogin.sh`
   - Or: `nextbrowser multilogin setup` (prints the right path)
4. **Always** run `nextbrowser multilogin doctor` before `exec --browser multilogin`; follow `next_steps` in JSON.
5. **`--profile reddit_default`** requires `MULTILOGIN_PROFILE_REDDIT_DEFAULT=<uuid>` (or use `--profile default` with only `MULTILOGIN_PROFILE_ID`).

## Guided setup

| OS | Command |
|----|---------|
| Windows | `.\scripts\setup-multilogin.ps1` |
| Linux / macOS | `chmod +x scripts/setup-multilogin.sh && ./scripts/setup-multilogin.sh` |

## Start MLX desktop app

| OS | How |
|----|-----|
| Windows | `%LOCALAPPDATA%\Multilogin X App\MLXDesktopApp.exe` |
| macOS | `open -a "Multilogin X App"` or install from multilogin.com |
| Linux | App menu, or set `MULTILOGIN_APP_EXE` (e.g. `/opt/mlx/desktop.bin`) |

## Manual CLI flow

```bash
nextbrowser multilogin setup
nextbrowser multilogin signin
nextbrowser multilogin automation-token
nextbrowser multilogin folders
nextbrowser multilogin profiles --folder-id <folder-uuid>
nextbrowser multilogin print-env
nextbrowser init --env
nextbrowser multilogin doctor
```

**macOS / Linux session env:**

```bash
export MULTILOGIN_FOLDER_ID="<folder-uuid>"
export MULTILOGIN_PROFILE_ID="<profile-uuid>"
export MULTILOGIN_PROFILE_REDDIT_DEFAULT="<profile-uuid>"
export NEXTBROWSER_BROWSER=multilogin
```

**Windows session env:**

```powershell
$env:MULTILOGIN_FOLDER_ID = "<folder-uuid>"
$env:MULTILOGIN_PROFILE_ID = "<profile-uuid>"
$env:MULTILOGIN_PROFILE_REDDIT_DEFAULT = "<profile-uuid>"
$env:NEXTBROWSER_BROWSER = "multilogin"
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
