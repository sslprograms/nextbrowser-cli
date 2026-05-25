---
name: nextbrowser-harness
description: >-
  Pairs with the browser-use skill for UI automation. nextbrowser manages Multilogin
  accounts (tier 3), connects CDP to browser-use, and handles scrape/tier lookup.
  Use browser-use for state/click/input — not nextbrowser exec. Ask user for account
  and credentials when needed.
version: 1.2.0
license: MIT
homepage: https://github.com/sslprograms/nextbrowser-cli
user-invocable: true
compatibility: >-
  Python 3.10+. Requires browser-use CLI + Multilogin X for tier-3. Install both skills.
platforms:
  - macos
  - linux
  - windows
---

# Nextbrowser Harness + browser-use

**UI automation = [browser-use](https://github.com/browser-use/browser-use) skill.**  
**MLX accounts + CDP = nextbrowser.**

Do not use `nextbrowser exec --action state` for clicking/typing. That path is deprecated for agents. Use **browser-use** after connecting Multilogin CDP.

## Install both skills

```bash
pip install -e ".[playwright,undetected]"
playwright install chromium
nextbrowser init --env
nextbrowser multilogin setup-wizard

# browser-use CLI (required for UI)
curl -fsSL https://browser-use.com/cli/install.sh | bash
browser-use doctor

# Both agent skills
nextbrowser agent install --force --with-browser-use
```

Load the **browser-use** skill in your agent (state / click / input commands). This skill covers MLX + accounts only.

## Tier 3 workflow (the one that works)

### 1. Ask the user

- **Which account?** → `nextbrowser account list`
- **New login?** → `nextbrowser account add <name> --create-mlx`
- **Need password?** → ask user (never use placeholders)

### 2. Connect Multilogin → browser-use (CDP)

```bash
nextbrowser browser-use connect --account reddit_main
```

JSON returns `cdp_url` and `browser_use_prefix`, e.g.:

```bash
browser-use --cdp-url "http://127.0.0.1:12345" open "https://www.reddit.com"
browser-use --cdp-url "http://127.0.0.1:12345" state
browser-use --cdp-url "http://127.0.0.1:12345" input 12 "username"
browser-use --cdp-url "http://127.0.0.1:12345" click 20
```

**Shorthand** (CDP saved from connect):

```bash
nextbrowser browser-use run open "https://www.reddit.com"
nextbrowser browser-use run state
nextbrowser browser-use run click 20
```

Follow the **browser-use skill** for full command list (`state`, `click`, `input`, `screenshot`, `eval`, …).

### 3. First login on a new account

```bash
nextbrowser account add my_site --create-mlx --site example.com
nextbrowser browser-use connect --account my_site
browser-use --cdp-url "<cdp from connect>" open "https://example.com/login"
browser-use --cdp-url "<cdp>" state
# ask user for credentials →
browser-use --cdp-url "<cdp>" input 2 "user@mail.com"
browser-use --cdp-url "<cdp>" input 3 "password"
browser-use --cdp-url "<cdp>" click 1
```

Session cookies persist in the Multilogin profile.

## What nextbrowser is for

| Task | Command |
|------|---------|
| Status / accounts / CDP info | `nextbrowser status` |
| List accounts | `nextbrowser account list` |
| Create MLX profile + name | `nextbrowser account add <name> --create-mlx` |
| Connect CDP for browser-use | `nextbrowser browser-use connect --account <name>` |
| Passthrough browser-use | `nextbrowser browser-use run state` |
| Read-only HTML | `nextbrowser scrape "<url>" --json` |
| MLX setup | `nextbrowser multilogin setup-wizard` |

## What browser-use is for

All page interaction — same as the official browser-use skill:

```bash
browser-use state
browser-use click 5
browser-use input 3 "text"
browser-use screenshot
browser-use eval "document.title"
```

Always run `state` first to get element indices.

## Live reference

```bash
nextbrowser status
```

Read `browser_use`, `accounts`, `tier3_automation`, `platform.cli`.

## Hard rules

1. **browser-use** for UI — **nextbrowser** for MLX connect + accounts + scrape.
2. Run `browser-use connect` (via nextbrowser) before `state` / `click`.
3. Ask user which account and for credentials when needed.
4. Do not write Playwright Python.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| browser-use not found | `curl -fsSL https://browser-use.com/cli/install.sh \| bash` |
| No CDP session | `nextbrowser browser-use connect --account <name>` |
| No account | `nextbrowser account add <name> --create-mlx` |
| MLX down | `nextbrowser multilogin doctor` |
| UI commands fail | `browser-use close` then reconnect |

Details: [references/browser-use-bridge.md](references/browser-use-bridge.md) · [references/troubleshooting.md](references/troubleshooting.md)

## Verify

```bash
browser-use doctor
nextbrowser browser-use doctor
nextbrowser account list
nextbrowser browser-use connect --account <name>
nextbrowser browser-use run state
```
