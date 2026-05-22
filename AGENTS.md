# Agent instructions — Nextbrowser Harness

Official CLI repo: [github.com/sslprograms/nextbrowser-cli](https://github.com/sslprograms/nextbrowser-cli)

This project is the `nextbrowser` CLI (`nextbrowser-harness` package). Prefer running commands over inventing browser code.

## CLI (use this prefix)

Run `nextbrowser status` and use the `platform.cli` value from JSON (e.g. `nextbrowser` or `python3 -m nextbrowser_harness.cli`).

## Common tasks

```bash
<cli> init --env
<cli> exec "<url>" --js "document.title"              # inject JS (agents)
<cli> exec "<url>" --steps-file examples/steps-reddit.json
<cli> scrape "<url>" --json
<cli> tier lookup "<url>"
<cli> account add <id>
<cli> account run <id> "eval:document.title" --url "<url>" --json
<cli> multilogin profiles
```

See `docs/AGENT_QUICKSTART.md` for OpenClaw / Claude / Cursor setup.

## Install skill for your host

```bash
<cli> agent list-hosts
<cli> agent install --host openclaw   # or claude, cursor, all
```

See `docs/AGENT_HOSTS.md` for OpenClaw, Claude Code, Cursor, Codex, Gemini, and others.

## Constraints

- Tier 1 = HTTP only; tier 2/3 need Playwright (`pip install -e ".[playwright]"`).
- Multilogin: start MLX desktop first (`MULTILOGIN_APP_EXE` on Windows, e.g. `%LOCALAPPDATA%\Multilogin X App\MLXDesktopApp.exe`), then `multilogin doctor` → token + folder/profile IDs. See `skills/nextbrowser-harness/SKILL.md` MLX section.
- `browse --browser native` works without MLX; `browse --browser multilogin` needs launcher on :45001.
- Linux: `playwright install-deps chromium` for headless Chrome.
