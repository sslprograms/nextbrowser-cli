---
name: nextbrowser-harness
description: Browser automation for AI agents — scrape, inject JS, Multilogin X profiles, Reddit/social flows. Use the nextbrowser CLI (OpenClaw, Claude Code, Cursor, Codex, shell).
homepage: https://github.com/sslprograms/nextbrowser-cli
user-invocable: true
metadata:
  {
    "openclaw":
      {
        "emoji": "🌐",
        "requires": { "anyBins": ["nextbrowser", "python", "python3"] },
        "os": ["darwin", "linux", "win32"]
      }
  }
---

# Nextbrowser Harness (agent skill)

Run **`nextbrowser`** (or `python -m nextbrowser_harness.cli`) with **`--json`** output. Always run `nextbrowser status` first and use `platform.cli` from the JSON.

## Install (once per machine)

```bash
git clone https://github.com/sslprograms/nextbrowser-cli.git
cd nextbrowser-cli
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[playwright]"
playwright install chromium
nextbrowser init --env
nextbrowser agent install --host openclaw    # or claude, cursor, all
```

Windows MLX app (start before Multilogin commands):

```powershell
$env:MULTILOGIN_APP_EXE = "$env:LOCALAPPDATA\Multilogin X App\MLXDesktopApp.exe"
if (-not (Get-Process MLXDesktopApp -EA SilentlyContinue)) { Start-Process $env:MULTILOGIN_APP_EXE }
```

## Inject scripts / automate pages (main agent commands)

**Run JavaScript in the page** (native or Multilogin browser):

```bash
nextbrowser exec "https://example.com" --js "document.title"
nextbrowser exec "https://www.reddit.com" --js-file examples/scripts/count-posts.js --tier 3 --screenshot /tmp/out.png
```

**Multi-step automation** (JSON or repeatable `--action`):

```bash
nextbrowser exec "https://www.reddit.com" --steps-file examples/steps-reddit.json --browser multilogin --profile reddit_default
nextbrowser exec "https://shop.com" --action "goto" --action "click:button.add-to-cart" --action "eval:document.body.innerText.slice(0,500)"
```

**Action syntax** (`--action` or inside JSON `actions` array):

| Action | Example |
|--------|---------|
| JS one-liner | `eval:return document.querySelectorAll('article').length` |
| JS file | `jsfile:./my-script.js` |
| Click | `click:button[type=submit]` |
| Fill | `fill:#email\|user@test.com` |
| Wait ms | `wait:3000` |
| Built-in | `goto`, `wait_load`, `title`, `scroll`, `screenshot`, `reddit_feed_check`, `final_url` |

**Account + script** (persistent profile per account):

```bash
nextbrowser account add reddit_01
nextbrowser account run reddit_01 "eval:document.title" --url "https://www.reddit.com" --js "return location.href"
```

Use `NEXTBROWSER_AUTOMATION=playwright` in env (recommended; no extra LLM API key).

## Scraping (no browser UI)

```bash
nextbrowser scrape "https://example.com/pricing" --json
nextbrowser tier lookup "https://reddit.com"
```

## Multilogin X

```bash
nextbrowser multilogin signin          # password MD5-hashed automatically
nextbrowser multilogin automation-token
nextbrowser multilogin folders
nextbrowser multilogin profiles --folder-id $MULTILOGIN_FOLDER_ID
nextbrowser multilogin doctor
nextbrowser multilogin start <profile-uuid> --folder-id <folder-uuid>
nextbrowser multilogin stop-all
```

Env for agents (OpenClaw `openclaw.json` → `skills.entries.nextbrowser-harness.env`):

- `NEXTBROWSER_BROWSER` — `native` or `multilogin`
- `NEXTBROWSER_AUTOMATION` — `playwright`
- `MULTILOGIN_FOLDER_ID`, `MULTILOGIN_PROFILE_ID` or `MULTILOGIN_PROFILE_REDDIT_DEFAULT`
- `MULTILOGIN_AUTOMATION_TOKEN` (optional if signin done)

## Browse (shortcut)

Same as `exec` with Reddit defaults:

```bash
nextbrowser browse "https://www.reddit.com" --browser native --tier 3 --js "document.title"
```

## Host-specific setup

| Host | Install skill | Config |
|------|---------------|--------|
| **OpenClaw** | `agent install --host openclaw` | `~/.openclaw/openclaw.json` → `skills.entries` env |
| **Claude Code** | `--host claude` | `~/.claude/skills/` + shell env |
| **Cursor** | `--host cursor` | `~/.cursor/skills/` + `.env` |
| **All** | `--host all` | Copies to every known skills dir |

Docs in repo: `docs/OPENCLAW.md`, `docs/AGENT_HOSTS.md`, `docs/AGENT_QUICKSTART.md`.

Config file: `~/.nextbrowser/config.yaml`
