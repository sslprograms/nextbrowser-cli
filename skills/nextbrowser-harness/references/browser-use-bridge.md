# MLX CDP session (legacy filename)

**Any AgentSkills host:** You are the agent (Cursor, Claude Code, Hermes, OpenClaw, etc.). After `nextbrowser connect`, use `nextbrowser ui state` and `ui click` / `ui type` — Playwright over MLX CDP. See `agent-host-drives-browser.md`.

## Stack

| Layer | Role |
|-------|------|
| **Multilogin X** | Anti-detect browser, proxy, cookies |
| **Playwright** | `connect_over_cdp` — state, click, type by index |
| **nextbrowser** | CLI + session file |

`nextbrowser connect` starts the MLX profile, captures the CDP URL, and saves it to `~/.nextbrowser/browser_use_session.json` (legacy name). Every `ui` command reconnects Playwright to that CDP URL. The MLX profile stays open until `disconnect` or `ui close`.

## Session file

```text
connect --account <name>
  → MLX start_profile
  → save CDP URL + account_id
login / ui state
  → Playwright attach, indexed elements
disconnect --account <name>
  → stop MLX profile, clear session
```

## Diagnostics

```bash
nextbrowser status
nextbrowser multilogin doctor
```
