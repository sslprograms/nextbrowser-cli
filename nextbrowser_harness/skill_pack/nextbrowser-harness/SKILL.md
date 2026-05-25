---
name: nextbrowser-harness
description: >-
  Browser automation via nextbrowser CLI. Tier 3 requires a named Multilogin account,
  connects over CDP, and persists logins in MLX profiles. Before automating, ask which
  account to use or whether to add a new login; ask for credentials when missing.
  Use state/click:N/type:N for UI. Scrape for read-only. Never write Playwright Python.
version: 1.1.0
license: MIT
homepage: https://github.com/sslprograms/nextbrowser-cli
user-invocable: true
compatibility: >-
  Python 3.10+. Playwright + Multilogin X launcher for tier-3 exec. macOS, Linux, Windows.
platforms:
  - macos
  - linux
  - windows
---

# Nextbrowser Harness

Use the **nextbrowser CLI** only (`platform.cli` from `nextbrowser status`). Do **not** write Playwright/Puppeteer/Selenium Python unless the user explicitly asks.

Deep reference: [references/automation.md](references/automation.md) · Commands: [references/commands.md](references/commands.md)

## When to use this skill

| User wants | Command | Account needed? |
|------------|---------|-----------------|
| Read page HTML / pricing | `scrape` | No |
| Click, type, login, browse | `exec` or `browse` | **Yes** if tier is 3 |
| Check site difficulty | `tier lookup` | No |

**Tier 3** (hard sites, Reddit, most real browsers): harness **always** launches **Multilogin**, connects via **CDP**, and requires `--account <registered_name>`.

## Mandatory: talk to the user before tier-3 automation

Do **not** run `exec`/`browse` on tier-3 sites until you have resolved account + credentials.

### 1. Pick or create an account

Run:

```bash
nextbrowser status    # accounts[] + platform.cli
nextbrowser account list
```

**Ask the user** (use their words):

- “Which account should I use?” — offer names from `account list`.
- “Should I add a new login?” — if yes, pick a short name (e.g. `reddit_main`) and run:

```bash
nextbrowser account add reddit_main --create-mlx --display-name "Reddit Main" --site reddit.com
```

That creates a **Multilogin browser profile** and registers the name. Cookies/session persist in MLX after the user logs in once.

Link an existing MLX profile instead:

```bash
nextbrowser account add reddit_main --mlx-profile <uuid>
```

### 2. Credentials for login flows

If the task needs sign-in and you **do not** have real username/password:

**Ask the user.** Do not use `USER`, `PASS`, `FROM_USER`, empty `--var`, or guessed values.

The CLI returns `agent_prompt` in JSON when blocked — show that guidance to the user.

## Tier 3 automation (Multilogin + CDP + `--account`)

### One-time setup

```bash
pip install -e ".[playwright,undetected]"
playwright install chromium
nextbrowser init --env
nextbrowser multilogin setup-wizard
nextbrowser multilogin doctor
nextbrowser agent install --force
```

### Indexed UI loop (same session via CDP)

1. List elements:

```bash
<cli> exec "<url>" --account <name> --action goto --action state
```

2. In the JSON response, find the action named `state`. Read numbered lines in `detail`:

```text
[12] textbox <input> Username
[15] textbox <input> Password
[20] button <button> Log in
```

3. Act using those indices (values from the user):

```bash
<cli> exec "<url>" --account <name> \
  --action "type:12|user@example.com" \
  --action "type:15|secret" \
  --action "click:20"
```

4. After navigation or DOM change → run `state` again before the next click/type.

Optional: `--action "find:Sign in"` · `--action logged-in` · `--recipe site.com/login --var username=... --var password=...`

### New account: first login (saves session in MLX)

```bash
<cli> account add my_site --create-mlx --site example.com
<cli> exec "https://example.com/login" --account my_site --action goto --action state
# ask user for credentials, then type/click by index
```

Later runs reuse the same `--account my_site` without re-entering credentials if MLX still has cookies.

## Read-only (no account, no Multilogin)

```bash
<cli> scrape "https://example.com/pricing" --json
```

## JSON errors agents must handle

| Field | Meaning |
|-------|---------|
| `success: false` | Command failed |
| `agent_prompt` | **Tell the user this** — missing account or credentials |
| `agent_fix` | Same guidance as `agent_prompt` when present |
| `connection: "cdp"` | Tier-3 run used Multilogin CDP |
| `account_id` | Account used for this run |

If `agent_prompt` mentions “Which saved account” → run `account list` and ask the user.

If it mentions credentials → ask for username/password, then retry with real `--var` or `type:N|value`.

## Action reference (indexed, default)

| Action | Example |
|--------|---------|
| `state` | List `[N]` interactive elements |
| `find:TEXT` | Indices matching label |
| `type:N\|text` | Type into element N |
| `click:N` | Click element N |
| `goto` | Navigate (usually first) |
| `eval:JS` | Run JavaScript |
| `logged-in` | Heuristic login check |

CSS mode only when selectors are known: `--element-search playwright`.

## Hard rules

1. Tier-3 `exec`/`browse` → **`--account <registered_name>`** (harness forces Multilogin + CDP).
2. **Ask** which account or whether to create a new login **before** automating.
3. **Ask** for credentials when login is required and unknown.
4. Do **not** edit `~/.nextbrowser/multilogin_tokens.yaml` by hand.
5. Do **not** guess CSS on SPAs/shadow DOM — use `state` + indices.
6. Use `exec`/`browse` for UI control — not `scrape`.

## Pitfalls

- **No `--account` on tier 3** → fails with `agent_prompt`; use `account list` / `account add`.
- **Placeholder credentials** → fails; ask user for real values.
- **`nextbrowser` not found** → use full `platform.cli` from `status`.
- **MLX launcher down** → `multilogin doctor`; start MLX desktop app.
- **`PROFILE_ALREADY_RUNNING`** → `multilogin stop-all`, retry.

More: [references/troubleshooting.md](references/troubleshooting.md) · MLX: [references/multilogin.md](references/multilogin.md)

## Verify

```bash
nextbrowser status
nextbrowser account list
nextbrowser multilogin doctor
nextbrowser exec "https://example.com" --account <name> --tier 3 --js "document.title"
```

Expect `success: true` and `connection: "cdp"` for tier-3 exec.
