# nextbrowser CLI reference

Use `platform.cli` from `nextbrowser status` if `nextbrowser` is not on PATH.

## Core

| Command | Purpose |
|---------|---------|
| `nextbrowser status` | `agent_must_know`, `stack`, `accounts`, `commands` |
| `nextbrowser init --env` | Bootstrap from environment |
| `nextbrowser scrape "<url>"` | Tiered HTTP fetch (no browser UI) |
| `nextbrowser tier lookup "<url>"` | Recommended tier + MLX hint |

## MLX connect (start here)

| Command | Purpose |
|---------|---------|
| `nextbrowser connect --account <name>` | Start MLX profile, save CDP session |
| `nextbrowser disconnect --account <name>` | Stop profile, clear session |
| `nextbrowser account list` | Saved accounts (name, MLX UUID, logged_in) |
| `nextbrowser account add <name> --create-mlx` | New MLX profile + name binding |
| `nextbrowser account add <name> --mlx-profile <uuid>` | Link existing MLX profile |
| `nextbrowser login <name> --url <url>` | One-shot open + state (+ optional credential indices) |

## UI (Playwright over MLX CDP)

| Command | Purpose |
|---------|---------|
| `nextbrowser ui state` | Indexed elements (how you see the page) |
| `nextbrowser ui open <url>` | Navigate |
| `nextbrowser ui click <N>` | Click by index |
| `nextbrowser ui type <N> "text"` | Type into element |
| `nextbrowser ui scroll down --pages 1` | Scroll |
| `nextbrowser ui require-login` | Exit 0 only if logged in (proof) |
| `nextbrowser ui verify --text "<exact>"` | Exit 0 if text visible (proof) |
| `nextbrowser ui situation` | URL + logged-in heuristic (exit 1 when logged out) |
| `nextbrowser ui close` | Same as disconnect |

Aliases: `nextbrowser state`, `click`, `input` when session exists.

## Optional autonomous agent-run

Uses **your** LLM API key from env (`OPENAI_API_KEY`, etc.) — not browser-use cloud.

| Command | Purpose |
|---------|---------|
| `nextbrowser account set-credentials <name> --username U --password P` | Local creds for agent-run |
| `nextbrowser agent-run "<task>" --account <name> --url <url>` | Autonomous task (optional) |

## Multilogin

| Command | Purpose |
|---------|---------|
| `nextbrowser multilogin setup-wizard` | Interactive MLX setup |
| `nextbrowser multilogin doctor` | Launcher + token check |
| `nextbrowser multilogin stop-all` | Emergency stop (outside a task only) |

## Agent skill install (any AgentSkills host)

```bash
nextbrowser agent install --host all --force
nextbrowser agent doctor
```

Single host: `--host cursor`, `--host claude`, `--host hermes`, `--host openclaw`, `--host codex`, `--host project`, etc.

## Environment

| Variable | Purpose |
|----------|---------|
| `MULTILOGIN_FOLDER_ID` | MLX folder UUID (setup-wizard) |
| `NEXTBROWSER_BROWSER_USE_SESSION` | Override session JSON path |
