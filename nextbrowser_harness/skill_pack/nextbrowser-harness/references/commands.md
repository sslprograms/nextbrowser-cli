# nextbrowser CLI reference (agents)

Always prefix commands with `platform.cli` from `nextbrowser status` when `nextbrowser` is not on PATH.

## Core

| Command | Purpose |
|---------|---------|
| `nextbrowser status` | Config, `platform.cli`, `agent_navigation` recipes |
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
| `--profile` | Profile key (e.g. `reddit_default`) |
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

## Accounts

```bash
nextbrowser account add reddit_01
nextbrowser account run reddit_01 "eval:document.title" --url "https://www.reddit.com"
```

## Agent skill install

```bash
nextbrowser agent list-hosts
nextbrowser agent install --host all --force
nextbrowser agent doctor
```

## Environment variables

| Variable | Values |
|----------|--------|
| `NEXTBROWSER_USE_CASE` | `scrape`, `accounts` |
| `NEXTBROWSER_BROWSER` | `native`, `multilogin` |
| `NEXTBROWSER_AUTOMATION` | `playwright` (recommended) |
| `NEXTBROWSER_PROXY` | `nodemaven`, `custom`, `none` |
| `MULTILOGIN_FOLDER_ID` | MLX folder UUID |
| `MULTILOGIN_PROFILE_ID` | Default profile UUID |
| `MULTILOGIN_PROFILE_<KEY>` | Per-profile UUID (uppercase key) |
