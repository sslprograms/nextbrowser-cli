# Agent quickstart — OpenClaw, Claude, Cursor, and others

This guide teaches **you** and **your agent** how to run browser automation (including **injecting JavaScript**) via the Nextbrowser Harness CLI.

---

## 1. One-time setup (your PC)

Official repo: **[sslprograms/nextbrowser-cli](https://github.com/sslprograms/nextbrowser-cli)**

```powershell
# Windows — clone or use your existing copy
cd C:\path\to\nextbrowser-cli   # after: git clone https://github.com/sslprograms/nextbrowser-cli.git
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[playwright]"
playwright install chromium

$env:NEXTBROWSER_USE_CASE = "scrape"
$env:NEXTBROWSER_BROWSER = "native"
$env:NEXTBROWSER_AUTOMATION = "playwright"
nextbrowser init --env
nextbrowser agent install --host all --force
```

Verify:

```bash
nextbrowser status
nextbrowser agent install --host all --force
nextbrowser agent doctor
```

---

## 2a. Hermes Agent

```bash
nextbrowser agent install --host hermes --force
```

Skill path: `~/.hermes/skills/browser-automation/nextbrowser-harness/` (or `%USERPROFILE%\.hermes\...` on Windows).

Set env in `~/.hermes/.env`:

```bash
export NEXTBROWSER_USE_CASE=scrape
export NEXTBROWSER_AUTOMATION=playwright
nextbrowser init --env
```

Use `/nextbrowser-harness` in chat or: `hermes --skills nextbrowser-harness`.

---

## 2. Install the skill for OpenClaw

```bash
nextbrowser agent install --host openclaw --force
```

Skill lands at: `C:\Users\<you>\.openclaw\skills\nextbrowser-harness\`

**Start a new OpenClaw session** after installing (skills load per session).

### OpenClaw config

Edit `%USERPROFILE%\.openclaw\openclaw.json` (Windows) or `~/.openclaw/openclaw.json`:

```json5
{
  skills: {
    entries: {
      "nextbrowser-harness": {
        enabled: true,
        env: {
          NEXTBROWSER_USE_CASE: "scrape",
          NEXTBROWSER_BROWSER: "native",
          NEXTBROWSER_AUTOMATION: "playwright",
          // Multilogin (optional):
          // NEXTBROWSER_BROWSER: "multilogin",
          // MULTILOGIN_FOLDER_ID: "your-folder-uuid",
          // MULTILOGIN_PROFILE_ID: "your-profile-uuid",
        },
      },
    },
  },
}
```

Or load skill from the repo without copying:

```json5
{
  skills: {
    load: {
      extraDirs: ["C:/path/to/nextbrowser-cli/skills"],
    },
  },
}
```

### What you say to OpenClaw

Examples:

- “Run `nextbrowser status` and use the CLI prefix from JSON.”
- “Open Reddit in the browser and count posts: `nextbrowser exec https://www.reddit.com --steps-file examples/steps-reddit.json --json`”
- “Inject JS: `nextbrowser exec https://example.com --js \"document.title\"`”

OpenClaw runs these via **shell** (`system.run` / exec tool) on the **same machine** as the browser.

---

## 3. Claude Code

```bash
nextbrowser agent install --host claude --force
```

Skill: `~/.claude/skills/nextbrowser-harness/`

Add to shell profile:

```bash
export NEXTBROWSER_AUTOMATION=playwright
export PATH="/path/to/stan-browser/.venv/bin:$PATH"
```

Or use full CLI from `nextbrowser status` → `platform.cli`.

---

## 4. Cursor

```bash
nextbrowser agent install --host cursor --force
```

Skill: `~/.cursor/skills/nextbrowser-harness/`

Project option:

```bash
nextbrowser agent install --host project --target workspace --force
# → ./skills/nextbrowser-harness/ in repo
```

Reference `AGENTS.md` in the repo root for Cursor agent rules.

---

## 5. Script injection cheat sheet

### Inline JavaScript

```bash
nextbrowser exec "https://www.reddit.com" --tier 3 --js "document.querySelectorAll('article').length"
```

### JavaScript file

Create `my-hook.js` (must be an expression or IIFE returning a value):

```javascript
(() => ({ title: document.title, n: document.links.length }))()
```

Run:

```bash
nextbrowser exec "https://example.com" --js-file my-hook.js
```

### Step file (best for complex flows)

See `examples/steps-reddit.json`:

```bash
nextbrowser exec "https://www.reddit.com" --steps-file examples/steps-reddit.json --screenshot %TEMP%\reddit.png
```

### Multilogin profile

```powershell
# Start MLX desktop app first
nextbrowser multilogin profiles --folder-id $env:MULTILOGIN_FOLDER_ID
nextbrowser exec "https://www.reddit.com" --browser multilogin --profile reddit_default --steps-file examples/steps-reddit.json
```

Set `MULTILOGIN_PROFILE_REDDIT_DEFAULT=<uuid>` or `MULTILOGIN_PROFILE_ID`.

---

## 6. Multilogin bootstrap (optional)

```bash
nextbrowser multilogin signin
nextbrowser multilogin automation-token
nextbrowser multilogin folders
nextbrowser multilogin profiles
```

Copy `folder_id` and profile `id` into OpenClaw env (section 2).

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| `nextbrowser` not found | Use `platform.cli` from `nextbrowser status` |
| Account run fails | Set `NEXTBROWSER_AUTOMATION=playwright` in config/env |
| MLX signin 400 | Password is auto MD5-hashed; use MLX app credentials |
| MLX browse “already running” | Harness reuses port; or `multilogin stop-all` |
| OpenClaw sandbox | Install Python + Playwright **inside** the sandbox image |
| Skill missing | `nextbrowser agent install --host openclaw --force` |

---

## 8. API reference

- MLX API: [Postman docs](https://documenter.getpostman.com/view/28533318/2s946h9Cv9)
- OpenClaw skills: [openclawx.cloud/tools/skills](https://openclawx.cloud/en/tools/skills)
- Full OpenClaw doc: [OPENCLAW.md](OPENCLAW.md)
