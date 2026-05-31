# Agent instructions

Run `nextbrowser status` first. `agent_must_know` in the JSON is canonical.

The harness has two use cases (Nextbrowser Harness MVP v1.3):

1. **Account automation** — drive a Multilogin X (MLX) profile with raw CDP.
2. **Web scraping** — tiered fetch with automatic 1→2→3 escalation.

## Account automation: MLX + raw CDP (no indexed shortcuts)

```bash
nextbrowser connect --account <name>
nextbrowser cdp navigate --account <name> https://www.reddit.com/r/sidehustle/
# OR step by step:
nextbrowser cdp send --account <name> Page.navigate --params '{"url":"https://..."}'
nextbrowser cdp survey --account <name>     # scrolls page + PNG per viewport — open with vision
nextbrowser cdp snapshot --account <name>   # verify after important actions
nextbrowser cdp send --account <name> Input.dispatchMouseEvent --params '{...}'
nextbrowser disconnect --account <name>
```

You (the host agent) are the controller. Every observe/act is a `cdp send` you choose.
No extra LLM API key and no external browser-automation product are used.

## Web scraping

```bash
nextbrowser scrape "<url>" --json     # no browser; tier DB + auto escalation
nextbrowser tier lookup <url>         # see recommended tier
```

## Never use (CLI returns error JSON)

- `nextbrowser ui …` (including `ui close`)
- `nextbrowser state` / `click` / `type` / `close` bare aliases
- Any indexed-click shortcut

## End task

`nextbrowser disconnect --account <name>` — never `multilogin stop-all` mid-task.

## Login (deterministic, recommended over hand-built clicks)

```bash
nextbrowser account set-credentials <name> --username "U" --password "P"
nextbrowser login <name> --url "https://site.com/login"
```

Connects MLX, finds the form, types credentials with trusted CDP `Input` events, submits,
verifies, and returns `logged_in` + before/after screenshots. Falls back to navigate+survey
if no credentials are stored. Never echoes the password.

Skill: `skills/nextbrowser-harness/SKILL.md` — install with `nextbrowser agent install --host all --force`.
