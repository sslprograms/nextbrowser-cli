---
name: nextbrowser-harness
description: >-
  Runs browser automation via the nextbrowser CLI — scrape pages, inject JavaScript,
  drive Multilogin X profiles, and automate Reddit or social sites. Use when the user
  asks to browse, scrape, fill forms, inject scripts, use Multilogin, or automate the
  web without writing Playwright Python.
version: 1.0.0
license: MIT
homepage: https://github.com/sslprograms/nextbrowser-cli
user-invocable: true
compatibility: >-
  Python 3.10+. Requires nextbrowser CLI (or python -m nextbrowser_harness.cli) and
  Playwright for tier 2/3 browser work. macOS, Linux, Windows.
platforms:
  - macos
  - linux
  - windows
metadata:
  openclaw:
    emoji: "🌐"
    requires:
      anyBins:
        - nextbrowser
        - python
        - python3
    os:
      - darwin
      - linux
      - win32
  hermes:
    tags:
      - browser
      - scraping
      - multilogin
      - playwright
      - cli
      - automation
    category: browser-automation
    requires_toolsets:
      - terminal
    homepage: https://github.com/sslprograms/nextbrowser-cli
    related_skills:
      - claude-code
      - codex
      - opencode
required_environment_variables:
  - name: NEXTBROWSER_AUTOMATION
    default: playwright
    prompt: Automation backend for browser exec
    help: Use playwright for JS injection without a separate LLM API key
    required_for: exec, browse, and account run
---

# Nextbrowser Harness

Drive browser automation through the **nextbrowser CLI** on the same machine as the agent. Always use shell commands — do not write standalone Playwright/Puppeteer/Selenium Python unless the user explicitly asks.

## When to Use

- User wants to **open a URL**, **click**, **fill forms**, or **run JavaScript** in a real browser
- User mentions **scraping**, **Reddit**, **Multilogin**, **anti-detect**, or **tiered** fetch
- User needs **read-only HTML** without launching a browser UI → use `scrape`
- User wants **persistent accounts/profiles** → use `account`

## Procedure

### 1. Resolve the CLI prefix

```bash
nextbrowser status
```

Use `platform.cli` and copy recipes from `agent_navigation` in the JSON output.

### 2. Bootstrap once (if not done)

```bash
pip install -e ".[playwright]"
playwright install chromium
nextbrowser init --env
nextbrowser agent install --host all --force
```

Set `NEXTBROWSER_AUTOMATION=playwright` (recommended).

### 3. Navigate (browser + actions)

**JavaScript in page:**

```bash
nextbrowser exec "https://example.com" --js "document.title"
nextbrowser exec "https://www.reddit.com" --js-file examples/scripts/count-posts.js --tier 3
```

**Step file (complex flows):**

```bash
nextbrowser exec "https://www.reddit.com" --steps-file examples/steps-reddit.json
```

**Actions on CLI:**

```bash
nextbrowser exec "https://shop.com" --action "fill:#email|user@test.com" --action "click:button.submit"
```

**Browse shortcut** (Reddit-oriented defaults):

```bash
nextbrowser browse "https://www.reddit.com" --js "document.title"
```

### 4. Read-only scrape (no browser UI)

```bash
nextbrowser scrape "https://example.com/pricing"
nextbrowser tier lookup "https://reddit.com"
```

### 5. Multilogin X (optional)

Start the MLX desktop app, then:

```bash
nextbrowser multilogin signin
nextbrowser multilogin automation-token
nextbrowser multilogin profiles --folder-id $MULTILOGIN_FOLDER_ID
nextbrowser exec "https://www.reddit.com" --browser multilogin --profile reddit_default --steps-file examples/steps-reddit.json
```

See [references/multilogin.md](references/multilogin.md).

### 6. Host install

```bash
nextbrowser agent install --host hermes --force
nextbrowser agent install --host openclaw --force
nextbrowser agent install --host all --force
nextbrowser agent doctor
```

Full command reference: [references/commands.md](references/commands.md).

## Action syntax

| Kind | Example |
|------|---------|
| JS one-liner | `eval:document.title` |
| JS file | `jsfile:./my-script.js` |
| Click | `click:button[type=submit]` |
| Fill | `fill:#email\|user@test.com` |
| Wait ms | `wait:3000` |
| Built-in | `goto`, `wait_load`, `title`, `scroll`, `reddit_feed_check`, `final_url` |

Use `--action` flags or a JSON `actions` array in a steps file.

## Pitfalls

- **`nextbrowser` not found** — use full `platform.cli` from `nextbrowser status`
- **Do not invent Playwright Python** — use `exec` / `browse` / `--js` / `--steps-file`
- **Account run fails** — set `NEXTBROWSER_AUTOMATION=playwright`
- **MLX signin 400** — harness MD5-hashes password; use MLX app credentials
- **PROFILE_ALREADY_RUNNING** — harness reuses CDP port; or `nextbrowser multilogin stop-all`
- **Reddit success:false** — captcha heuristics may fire while partial actions still ran
- **Sandboxed agent** — Python + Playwright must exist **inside** the sandbox, not only on host

More fixes: [references/troubleshooting.md](references/troubleshooting.md).

## Verification

```bash
nextbrowser agent doctor          # skill paths + bundled SKILL.md
nextbrowser scrape "https://example.com"
nextbrowser exec "https://example.com" --js "document.title"
```

Expect JSON with `success: true` for example.com. Config: `~/.nextbrowser/config.yaml`.

## Host paths

| Host | Install | Skill location |
|------|---------|----------------|
| Hermes | `--host hermes` | `~/.hermes/skills/browser-automation/nextbrowser-harness/` |
| OpenClaw | `--host openclaw` | `~/.openclaw/skills/nextbrowser-harness/` |
| Claude Code | `--host claude` | `~/.claude/skills/nextbrowser-harness/` |
| Cursor | `--host cursor` | `~/.cursor/skills/nextbrowser-harness/` |
| Project | `--host project --target workspace` | `./skills/nextbrowser-harness/` |
| All | `--host all` | Every known managed skills dir |

Repo docs: `docs/AGENT_QUICKSTART.md`, `docs/AGENT_HOSTS.md`, `docs/OPENCLAW.md`.
