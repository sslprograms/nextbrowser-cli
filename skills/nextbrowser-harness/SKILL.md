---
name: nextbrowser-harness
description: >-
  Multimodular browser harness (MVP v1.3). Two use cases: account automation
  (Multilogin + CDP) and tiered scraping (HTTP → headless → headful). Single
  command for login (keeps browser open, persists cookies). Pairs with the
  browser-use skill for UI control. Ask user for account name and credentials
  when missing.
version: 1.3.0
license: MIT
homepage: https://github.com/sslprograms/nextbrowser-cli
user-invocable: true
compatibility: >-
  Python 3.10+. Multilogin X + browser-use CLI for tier 3. macOS, Linux, Windows.
platforms:
  - macos
  - linux
  - windows
---

# Nextbrowser Harness v1.3

Run `nextbrowser status` first. `agent_must_know` in the JSON is canonical.

Pair this skill with the **[browser-use](https://github.com/browser-use/browser-use)** skill — it owns all UI primitives.

## Architecture (4-layer stack)

| Layer | MVP integrations | Default |
|-------|------------------|---------|
| Browser | native · multilogin · gologin · octo | native (anti-detect tuned) |
| Proxy | nodemaven · custom · none | nodemaven residential |
| Automation | browser_use · playwright | browser_use (via CDP) |
| CAPTCHA | optional 2Captcha / CapMonster token | off |

LLM inherits from the host agent — no API key prompt.

## Two use cases

### 1. Account automation (tier 3 — Multilogin + CDP)

Single reliable login command:

```bash
nextbrowser login <account_name> --url <login_url> \
  --username-index N --password-index N --submit-index N \
  --username "<user>" --password "<pass>"
```

What it does:

1. Creates the Multilogin profile if `<account_name>` doesn't exist yet.
2. Connects MLX over CDP (browser stays open — keep-alive).
3. Opens the URL, runs `state` to list element indices.
4. If indices + credentials are provided, runs `input` → `input` → `click` → `state` in **one chain**.
5. Returns JSON: `cdp_url`, `mlx_profile_id`, `state`, `logged_in`, `next_commands`.

Two-pass login (when you need indices first):

```bash
# Pass 1: open and read indices
nextbrowser login reddit_main --url "https://www.reddit.com/login"
# → returns state output with [N] labels

# Pass 2: feed real credentials + indices
nextbrowser login reddit_main --url "https://www.reddit.com/login" \
  --username-index 12 --password-index 15 --submit-index 20 \
  --username "$RU" --password "$RP"
```

Then continue with the same open browser:

```bash
nextbrowser ui state
nextbrowser ui click 5
nextbrowser ui type 3 "hello"
nextbrowser ui eval "document.title"
nextbrowser ui screenshot out.png
nextbrowser ui close      # end of task — disconnects MLX cleanly
```

### 2. Web scraping (3 tiers, auto-escalation)

```bash
nextbrowser scrape "<url>" --json     # tier from DB, escalates on failure
nextbrowser tier lookup "<url>"       # show recommended tier + MLX hint
```

| Tier | What | When |
|------|------|------|
| 1 | HTTP only | APIs, static HTML |
| 2 | Headless browser | Most modern sites |
| 3 | Headful + Multilogin + residential | Reddit-class anti-bot |

Tier-3 scraping needs a registered account (same as use case 1).

## Onboarding (under 60 seconds)

```bash
pip install -e ".[playwright,undetected]"
playwright install chromium
nextbrowser init --env
nextbrowser multilogin setup-wizard
curl -fsSL https://browser-use.com/cli/install.sh | bash
nextbrowser agent install --force --with-browser-use
```

## Account management

```bash
nextbrowser account list
nextbrowser account add <name> --create-mlx --site reddit.com
nextbrowser account add <name> --mlx-profile <existing-uuid>
```

`--create-mlx` calls Multilogin API to create a new browser profile in your folder and binds it to the account name. Verify the profile appears in the Multilogin X app.

## Agent rules (non-negotiable)

1. **`nextbrowser status`** first — read `agent_must_know`.
2. **Ask user** which account to use; ask for credentials when missing.
3. **One `login` call**, not separate exec/run per field.
4. **`nextbrowser ui ...`** for follow-up actions — browser stays open.
5. **`nextbrowser ui close`** only when the task is fully done.
6. **No** `browser-use close`, `multilogin stop-all`, or raw Playwright Python during a task.
7. Scrape-only? `nextbrowser scrape URL --json` — no account needed.

## Command map

| Goal | Command |
|------|---------|
| Read agent rules | `nextbrowser status` |
| First-time login | `nextbrowser login <account> --url <url>` |
| Re-use session | `nextbrowser ui state` / `click N` / `type N text` |
| End task | `nextbrowser ui close` |
| Scrape | `nextbrowser scrape "<url>" --json` |
| Tier check | `nextbrowser tier lookup "<url>"` |
| MLX health | `nextbrowser multilogin doctor` |

## References

- [references/browser-use-bridge.md](references/browser-use-bridge.md)
- [references/troubleshooting.md](references/troubleshooting.md)
- [references/commands.md](references/commands.md)

## Verify

```bash
nextbrowser status
nextbrowser account list
nextbrowser multilogin doctor
browser-use doctor
nextbrowser login <name> --url https://example.com
nextbrowser ui state
nextbrowser ui close
```
