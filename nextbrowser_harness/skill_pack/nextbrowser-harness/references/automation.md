# Automation guide (tier 3 = Multilogin + CDP + named account)

## Decision flow

```text
User wants browser automation?
  ├─ Read-only HTML → scrape (no account)
  └─ Clicks / login / JS → exec or browse
        ├─ tier lookup URL (or status) — tier 3?
        │     ├─ Ask: which account? (account list)
        │     ├─ Or: add new login? (account add NAME --create-mlx)
        │     ├─ Login needed + no credentials? → ask user
        │     └─ exec --account NAME --action goto --action state → click:N / type:N|val
        └─ tier 1–2 → exec may use native browser (account optional)
```

Tier **3** always: **Multilogin profile** + **CDP** + **`--account`**.

## Agent phrases (copy/adapt)

**Account**

- “Which saved account should I use? I see: …” (from `account list`)
- “Would you like me to add a new login? I can create one named …”

**Credentials**

- “I need your username/email and password for … to continue.”
- Never proceed with placeholders or invented passwords.

## Commands

| Step | Command |
|------|---------|
| CLI prefix | `nextbrowser status` → `platform.cli` |
| List accounts | `<cli> account list` |
| New MLX profile + name | `<cli> account add <name> --create-mlx --display-name "…" --site domain.com` |
| Link existing MLX UUID | `<cli> account add <name> --mlx-profile <uuid>` |
| List elements | `<cli> exec "<url>" --account <name> --action goto --action state` |
| Click/type | `<cli> exec "<url>" --account <name> --action "click:5" --action "type:3\|text"` |
| Login recipe | `<cli> exec "<url>" --account <name> --recipe site/login --var username=X --var password=Y` |
| Scrape only | `<cli> scrape "<url>" --json` |

## First login (session saved in Multilogin)

1. `account add my_site --create-mlx`
2. `exec … --account my_site --action goto --action state`
3. Ask user for credentials
4. `exec … --account my_site --action "type:N|user" --action "type:M|pass" --action "click:K"`
5. Optional: `--action logged-in`

Future runs with `--account my_site` reuse MLX cookies when still valid.

## `nextbrowser status` JSON

| Key | Use |
|-----|-----|
| `platform.cli` | Prefix every command |
| `accounts` | Saved names, `logged_in`, `mlx_profile_id` |
| `tier3_automation` | Policy: multilogin, cdp, ask-user |
| `how_to_automate` | Full workflow steps |
| `agent_navigation` | Command templates |

## On failure

Read `agent_prompt` and `agent_fix` in exec JSON — they tell you to ask the user for account or credentials.
