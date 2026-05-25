# nextbrowser CLI reference (agents)

Always prefix commands with `platform.cli` from `nextbrowser status` when `nextbrowser` is not on PATH.

## Core

| Command | Purpose |
|---------|---------|
| `nextbrowser status` | `platform.cli`, `accounts`, `tier3_automation`, `how_to_automate` |
| `nextbrowser account list` | Named Multilogin accounts for tier 3 |
| `nextbrowser account add <id> --create-mlx` | Create MLX profile + register name |
| `nextbrowser init --env` | Bootstrap from environment variables |
| `nextbrowser scrape "<url>"` | Tiered HTTP fetch (no browser UI) |
| `nextbrowser exec "<url>"` | Browser + JS / actions / steps file |
| `nextbrowser browse "<url>"` | Same as exec with Reddit-oriented defaults |
| `nextbrowser tier lookup "<url>"` | Recommended tier for domain |

## exec / browse flags

| Flag | Example |
|------|---------|
| `--js` | `--js "document.title"` |
| `--js-file` | `--js-file examples/scripts/count-posts.js` |
| `--steps-file` | `--steps-file examples/steps-reddit.json` |
| `--action` | Repeatable: `--action "click:button.submit"` |
| `--tier` | `1`, `2`, or `3` |
| `--browser` | `native` or `multilogin` |
| `--account` / `--profile` | Named account (required for tier 3), e.g. `reddit_main` |
| `--screenshot` | Output PNG path |
| `--headless` | Headless native browser |
| `--keep-open` | Leave MLX browser running (exec only) |

## Steps file format

```json
{
  "url": "https://www.reddit.com",
  "actions": [
    "goto",
    "wait_load",
    "title",
    "eval:document.querySelectorAll('article').length",
    "final_url"
  ]
}
```

URL in JSON overrides the CLI URL argument when present.

## Accounts (tier 3)

```bash
nextbrowser account list
nextbrowser account list --json
nextbrowser account add reddit_main --create-mlx --display-name "Reddit" --site reddit.com
nextbrowser account add reddit_main --mlx-profile <uuid>   # link existing MLX profile
nextbrowser exec "https://www.reddit.com" --account reddit_main --action goto --action state
nextbrowser account run reddit_main "eval:document.title" --url "https://www.reddit.com"
```

`--account` is required on tier-3 `exec`/`browse`. Harness uses Multilogin + CDP automatically.

## Agent skill install

```bash
nextbrowser agent install --force
nextbrowser agent doctor
```

See [automation.md](automation.md) for the element workflow (not host-specific).

## Environment variables

| Variable | Values |
|----------|--------|
| `NEXTBROWSER_USE_CASE` | `scrape`, `accounts` |
| `NEXTBROWSER_BROWSER` | `native`, `multilogin` |
| `NEXTBROWSER_DRIVER` | `undetected` (default), `playwright` |
| `NEXTBROWSER_AUTOMATION` | `playwright` (recommended) |
| `NEXTBROWSER_PROXY` | `none` (default), `nodemaven`, `custom` |
| `MULTILOGIN_FOLDER_ID` | MLX folder UUID |
| `MULTILOGIN_PROFILE_ID` | Default profile UUID |
| `MULTILOGIN_PROFILE_<KEY>` | Per-profile UUID (uppercase key) |
