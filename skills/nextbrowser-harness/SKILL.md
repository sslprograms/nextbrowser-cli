---
name: nextbrowser-harness
description: >-
  Multilogin accounts + CDP for browser-use. Agents MUST keep MLX browser open during
  login (use browser-use chain), ask user for account/credentials, create profiles with
  account add --create-mlx, disconnect when done. UI via browser-use skill only.
version: 1.3.0
license: MIT
homepage: https://github.com/sslprograms/nextbrowser-cli
user-invocable: true
compatibility: >-
  Python 3.10+. browser-use CLI + Multilogin X. Install both skills via agent install --with-browser-use.
platforms:
  - macos
  - linux
  - windows
---

# Nextbrowser + browser-use

**Read this first.** Run `nextbrowser status` and follow `agent_must_know` in the JSON.

Load the **[browser-use](https://github.com/browser-use/browser-use) skill** for UI. This skill covers Multilogin accounts and keeping the browser open.

## Agent must know (non-negotiable)

1. **UI = browser-use only** — not `nextbrowser exec --action state` / `click`.
2. **Ask the user** before tier-3 work: which account? new login? username/password?
3. **Create MLX profile:** `nextbrowser account add <name> --create-mlx` — check `mlx_profile_id` in JSON and in Multilogin app.
4. **Connect once:** `nextbrowser browser-use connect --account <name>` — browser **stays open**.
5. **Whole login in ONE chain** — cookies save in Multilogin only if the profile is not closed between steps:
   ```bash
   nextbrowser browser-use chain open "<url>" state "input 12 REAL_USER" "input 15 REAL_PASS" "click 20"
   ```
6. **Never during login:** `browser-use close`, `multilogin stop-all`, separate `exec`/`run` per field.
7. **When done:** `nextbrowser browser-use disconnect --account <name>`.
8. **Scrape only:** `nextbrowser scrape "<url>" --json` (no account).

## Quick start

```bash
nextbrowser status
nextbrowser agent install --force --with-browser-use
nextbrowser multilogin setup-wizard
curl -fsSL https://browser-use.com/cli/install.sh | bash
```

## Full login flow (copy for agents)

```bash
# 1. Ask user which account; or create:
nextbrowser account add reddit_main --create-mlx --display-name "Reddit Main"

# 2. Connect — MLX stays open
nextbrowser browser-use connect --account reddit_main

# 3. ONE chain (get indices from state step; credentials from user)
nextbrowser browser-use chain open "https://www.reddit.com/login" state "input 12 USER" "input 15 PASS" "click 20"

# 4. Only when user confirms login is complete
nextbrowser browser-use disconnect --account reddit_main
```

## Command roles

| Tool | Use for |
|------|---------|
| **nextbrowser** | `status`, `account list/add`, `browser-use connect/chain/disconnect`, `scrape`, MLX setup |
| **browser-use** | `state`, `click`, `input`, `screenshot`, `eval` (after connect) |

## Live rules from CLI

```bash
nextbrowser status
```

Fields: `agent_must_know`, `browser_use`, `accounts`, `agent_navigation`, `how_to_automate`.

## Hard rules

- Chain login — do not split into multiple exec/run commands.
- Keep browser open until `disconnect`.
- Real credentials from user only.
- No Playwright Python.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Browser closes mid-login | Use `browser-use chain`, not per-step exec |
| Profile missing in MLX | `account add ... --create-mlx` again; `multilogin doctor` |
| No CDP | `browser-use connect --account <name>` first |

[references/browser-use-bridge.md](references/browser-use-bridge.md) · [references/troubleshooting.md](references/troubleshooting.md)
