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
---

# Nextbrowser Harness

Drive browser automation through the **nextbrowser CLI** on the same machine as the agent. Always use shell commands — do not write standalone Playwright/Puppeteer/Selenium Python unless the user explicitly asks.

## When to Use

- User wants to **open a URL**, **click**, **fill forms**, or **run JavaScript** in a real browser
- User mentions **scraping**, **Reddit**, **Multilogin**, **anti-detect**, or **tiered** fetch
- User needs **read-only HTML** without launching a browser UI → use `scrape`
- User wants **persistent accounts/profiles** → use `account`

## Agent rule: follow the user's browser instructions

When the user describes a multi-step browser task (login, search, click, comment, scrape):

1. **Do not** write standalone Playwright/Python — use `nextbrowser exec` only.
2. **Translate** each user step into `--action` flags or a JSON steps file, then run one command.
3. **Modern sites (Reddit, SPAs, shadow DOM):** use `--element-search indexed` (default) — run `state`, read numbered `[N]` elements, then `click:N` / `type:N|value`. Same *workflow* as browser-use; **no browser-use package required**.
3. **MLX / Multilogin:** before first `exec --browser multilogin`, run `multilogin doctor`; if launcher fails on Linux, run `multilogin fix-linux-launcher`.
4. **Native anti-detect:** default driver is undetected Chrome (`NEXTBROWSER_DRIVER=undetected`); use `--browser native --tier 3`.
5. **Report** the JSON result (`success`, `actions`, `error`) back to the user.

Example — user says: open site, wait, click login, fill email/password, submit:

```bash
pip install -e ".[playwright,undetected]"
python -m nextbrowser_harness.cli exec "https://www.reddit.com/login" --tier 3 --browser multilogin \
  --element-search indexed \
  --action goto --action state --action "type:12|USER" --action "type:15|PASS" --action "click:20"
```

(Indices **12**, **15**, **20** are examples — always copy real indices from the `state` action output.)

CSS fallback (`--element-search playwright` or default on plain Playwright launch):

```bash
nextbrowser exec "https://example.com" --tier 3 --action goto --action "type:#email|user@example.com"
```

Prefer a steps file for long flows:

```json
{
  "url": "https://example.com",
  "actions": ["goto", "wait-for:#email", "type:#email|user@test.com", "click:button.submit", "final_url"]
}
```

```bash
nextbrowser exec "https://example.com" --steps-file ./my-steps.json --browser multilogin --tier 3
```

## Procedure

### 1. Resolve the CLI prefix

```bash
nextbrowser status
```

Use `platform.cli` and copy recipes from `agent_navigation` in the JSON output.

### 2. Bootstrap once (if not done)

```bash
pip install -e ".[playwright,undetected]"
playwright install chromium
nextbrowser init --env
nextbrowser agent install --host all --force
```

`init --env` sets `NEXTBROWSER_AUTOMATION=playwright` and `NEXTBROWSER_DRIVER=undetected` — no API key or secret prompt needed.

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
nextbrowser exec "https://shop.com" --action "type:#email|user@test.com" --action "click:button.submit"
```

**Site recipes (Reddit login, upvote, …):**

```bash
nextbrowser recipes
nextbrowser exec "https://www.reddit.com" --recipe reddit.com/login \
  --var username=USER --var password=PASS --browser multilogin --tier 3
```

**Browse shortcut** (Reddit-oriented defaults):

```bash
nextbrowser browse "https://www.reddit.com" --js "document.title"
```

### 4. Tier selection (automatic unless you force it)

| Command | Without `--tier` |
|---------|------------------|
| `scrape` | Looks up domain in tier DB → starts there → **escalates 1→2→3** until success |
| `exec` / `browse` | Uses **recommended tier for URL** from DB (e.g. Reddit = tier 3); browser work uses at least tier 2 |
| `tier lookup` | Shows recommended tier + whether to use Multilogin |

```bash
nextbrowser tier lookup "https://www.reddit.com"
nextbrowser scrape "https://example.com/pricing"
nextbrowser exec "https://www.reddit.com"   # no --tier = auto from DB
```

**Multilogin recommendation:** If `browser` is `native` but the site needs tier 2/3 (or `use_case=accounts`), JSON includes `multilogin_recommendation` — tell the user to run `nextbrowser multilogin setup-wizard` and use `--browser multilogin`.

### 5. Read-only scrape (no browser UI)

```bash
nextbrowser scrape "https://example.com/pricing"
nextbrowser tier lookup "https://reddit.com"
```

### 6. Multilogin X (optional)

**Agents:** follow [references/multilogin.md](references/multilogin.md) — run `setup-wizard`; do **not** patch `multilogin_tokens.yaml` or store passwords.

**Recommended (all platforms):**

```bash
nextbrowser multilogin setup-wizard
nextbrowser multilogin doctor
```

**Windows script:**

```powershell
.\scripts\setup-multilogin.ps1
```

**Linux / macOS script:**

```bash
chmod +x scripts/setup-multilogin.sh
./scripts/setup-multilogin.sh
```

**Linux .deb broken launcher** (`/opt/mlx/usr/bin/mlx` points at wrong `agent.bin`):

```bash
nextbrowser multilogin fix-linux-launcher
nextbrowser multilogin doctor
```

Correct binary path: `/opt/mlx/opt/mlx/agent.bin`. Harness auto-fixes this on `setup-wizard` and before MLX `exec`.

**Run with MLX profile** (needs `MULTILOGIN_PROFILE_REDDIT_DEFAULT` when using `--profile reddit_default`):

```bash
nextbrowser exec "https://www.reddit.com" --browser multilogin --profile reddit_default --tier 3
```

### 7. Host install

```bash
nextbrowser agent install --host hermes --force
nextbrowser agent install --host openclaw --force
nextbrowser agent install --host all --force
nextbrowser agent doctor
```

Full command reference: [references/commands.md](references/commands.md).

## Action syntax

### Indexed mode (`--element-search indexed`, default)

Numbered interactive elements for the agent (built into the harness):

| Kind | Example |
|------|---------|
| List elements | `state` — returns numbered interactive elements in JSON `detail` |
| Find index | `find:Sign in` — returns matching indices |
| Click | `click:5` or `click:@5` |
| Type | `type:3\|mypassword` |
| Wait for index | `wait-for:12` |
| Navigation / JS | `goto`, `eval:...`, `wait_load`, `title`, `final_url` |

### Playwright CSS mode (default on non-CDP launch)

| Kind | Example |
|------|---------|
| Type / fill | `type:#email\|user@test.com` (keyboard; works on web components) |
| Click | `click:button.submit` or `deep-click:host >> button` |
| Wait | `wait-for:#id`, `wait-for-nav:`, `wait-for-text:OK` |

Use `--action` flags, `--steps-file`, or `--recipe site.com/flow`.

## Pitfalls

- **`nextbrowser` not found** — use full `platform.cli` from `nextbrowser status`
- **Do not invent Playwright Python** — use `exec` / `browse` / `--js` / `--steps-file`
- **Account run fails** — set `NEXTBROWSER_AUTOMATION=playwright`
- **MLX signin 400 / 401 after signin** — run `multilogin signin` (clears stale `automation_token`); session `token` beats expired automation in YAML
- **Reddit login fill fails** — use `type:faceplate-text-input#login-username|user` or `fill:` (inner input fallback)
- **Reddit upvote** — use `shadow-click:` or `reddit_upvote`, not plain `click:`
- **config.yaml reverted to folder-1** — `init --env` no longer wipes UUIDs; remove placeholder IDs from `.env`; run `multilogin setup-wizard`
- **MLX doctor fails** — start desktop app; run `nextbrowser multilogin setup-wizard`
- **exec --profile reddit_default fails** — set `MULTILOGIN_PROFILE_REDDIT_DEFAULT` to the profile UUID
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
