# nextbrowser CLI reference

Use `platform.cli` from `nextbrowser status` if `nextbrowser` is not on PATH.

## Core

| Command | Purpose |
|---------|---------|
| `nextbrowser status` | `agent_must_know`, `stack`, `accounts`, `commands` |
| `nextbrowser init --env` | Bootstrap from environment |
| `nextbrowser scrape "<url>"` | Tiered HTTP fetch (no browser UI) |
| `nextbrowser tier lookup "<url>"` | Recommended tier + MLX hint |

## AI agent-run (autonomous browser control)

| Command | Purpose |
|---------|---------|
| `nextbrowser agent-run "<task>" --account <name>` | Run AI agent over MLX CDP |
| `nextbrowser agent-run "<task>" --account <name> --url <url>` | Navigate first, then run task |
| `nextbrowser agent-run "<task>" --model gpt-4o` | Choose LLM model |
| `nextbrowser agent-run "<task>" --captcha` | Enable captcha solving guidance |
| `nextbrowser agent-run "<task>" --approval` | Enable content approval (social posts) |
| `nextbrowser agent-run "<task>" --max-steps 50` | Limit agent steps |

## Account automation (use case 1)

| Command | Purpose |
|---------|---------|
| `nextbrowser account list` | Saved accounts (name, MLX UUID, logged_in) |
| `nextbrowser account add <name> --create-mlx` | New MLX profile + name binding |
| `nextbrowser account add <name> --mlx-profile <uuid>` | Link existing MLX profile |
| `nextbrowser login <name> --url <url>` | One-shot login (open + state + optional credentials) |
| `nextbrowser login <name> --url <url> --username U --password P --username-index 12 --password-index 15 --submit-index 20` | Chained login |
| `nextbrowser ui state` | List clickable elements |
| `nextbrowser ui open <url>` | Navigate |
| `nextbrowser ui click <N>` | Click by index |
| `nextbrowser ui type <N> "text"` | Type into element |
| `nextbrowser ui keys "Enter"` | Send keys |
| `nextbrowser ui eval "<js>"` | Run JavaScript |
| `nextbrowser ui screenshot [path]` | Screenshot |
| `nextbrowser ui chain "open URL" "state" "click 5"` | Multi-step in one shell |
| `nextbrowser ui run <browser-use args...>` | Raw browser-use passthrough |
| `nextbrowser ui close` | End task: disconnect + stop MLX |

## Multilogin

| Command | Purpose |
|---------|---------|
| `nextbrowser multilogin setup-wizard` | Interactive MLX setup |
| `nextbrowser multilogin doctor` | Launcher + token check |
| `nextbrowser multilogin folders` | List workspace folders |
| `nextbrowser multilogin profiles` | Search profiles |
| `nextbrowser multilogin stop-all` | Emergency stop (use only outside a task) |

## browser-use bridge

| Command | Purpose |
|---------|---------|
| `nextbrowser browser-use connect --account <name>` | Underlying connect (login wraps this) |
| `nextbrowser browser-use disconnect --account <name>` | Same as `ui close` |
| `nextbrowser browser-use doctor` | browser-use CLI + saved session |
| `nextbrowser browser-use install-skill` | Download official browser-use SKILL.md |

## Agent skill install

```bash
nextbrowser agent install --force --with-browser-use
nextbrowser agent doctor
```

## Environment

| Variable | Purpose |
|----------|---------|
| `NEXTBROWSER_USE_CASE` | `scrape` or `accounts` |
| `NEXTBROWSER_BROWSER` | `native` / `multilogin` |
| `NEXTBROWSER_DRIVER` | `undetected` (default) / `playwright` |
| `NEXTBROWSER_PROXY` | `none` / `nodemaven` / `custom` |
| `MULTILOGIN_FOLDER_ID` | MLX folder UUID (set by setup-wizard) |
