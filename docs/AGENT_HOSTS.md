# AI agent hosts (OpenClaw, Claude Code, Cursor, and more)

Nextbrowser Harness works with any agent that can **run shell commands** and load **[AgentSkills](https://agentskills.io/)**-style `SKILL.md` folders.

One install command targets multiple hosts (Linux, macOS, Windows):

```bash
nextbrowser agent list-hosts
nextbrowser agent install --host all      # ~/.openclaw, ~/.claude, ~/.cursor, …
nextbrowser agent install --host claude   # Claude Code only
nextbrowser agent doctor
```

Legacy alias: `nextbrowser openclaw install` (= `--host openclaw`).

---

## Supported hosts

| Host ID | Product | Skill location (managed) | Docs |
|---------|---------|--------------------------|------|
| `hermes` | Hermes Agent | `~/.hermes/skills/browser-automation/nextbrowser-harness/` | [Hermes skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) |
| `openclaw` | OpenClaw | `~/.openclaw/skills/nextbrowser-harness/` | [OpenClaw skills](https://openclawx.cloud/en/tools/skills) |
| `claude` | Claude Code | `~/.claude/skills/nextbrowser-harness/` | [Claude Code skills](https://code.claude.com/docs/en/skills) |
| `cursor` | Cursor | `~/.cursor/skills/nextbrowser-harness/` | [Cursor docs](https://docs.cursor.com/) |
| `continue` | Continue | `~/.continue/skills/nextbrowser-harness/` | [Continue](https://docs.continue.dev/) |
| `roo` | Roo Code | `~/.roo/skills/nextbrowser-harness/` | [Roo Code](https://docs.roocode.com/) |
| `codex` | OpenAI Codex / CLI | `~/.codex/skills/nextbrowser-harness/` | [AgentSkills](https://agentskills.io/) |
| `gemini` | Gemini CLI | `~/.gemini/skills/nextbrowser-harness/` | [AgentSkills](https://agentskills.io/) |
| `opencode` | OpenCode | `~/.config/opencode/skills/nextbrowser-harness/` | Host-specific |
| `kilocode` | Kilo Code | `~/.kilocode/skills/nextbrowser-harness/` | [Kilo Code](https://kilocode.ai/docs/) |
| `windsurf` | Windsurf / Cline | `~/.codeium/windsurf/skills/nextbrowser-harness/` | [Windsurf](https://docs.windsurf.com/) |
| `project` | Any (repo-local) | `./skills/nextbrowser-harness/` | Portable in git |

Project-local install (shared via git):

```bash
nextbrowser agent install --host project --target workspace
# or: cp -R skills/nextbrowser-harness .claude/skills/
```

---

## How every host uses the harness

1. **Skill** teaches the model which CLI commands to run.
2. **Agent exec** runs shell on the gateway machine (same OS as browser automation).
3. **`nextbrowser`** (or `python3 -m nextbrowser_harness.cli`) performs scrape/account work.

Check the command prefix on your machine:

```bash
nextbrowser status   # → platform.cli
nextbrowser agent doctor
```

---

## Per-host configuration

### Hermes Agent

Install: `nextbrowser agent install --host hermes`

Skill path: `~/.hermes/skills/browser-automation/nextbrowser-harness/` (Hermes category layout).

Set env in `~/.hermes/.env` or run `hermes setup`:

```bash
export NEXTBROWSER_USE_CASE=scrape
export NEXTBROWSER_AUTOMATION=playwright
nextbrowser init --env
```

Use slash command `/nextbrowser-harness` or preload: `hermes --skills nextbrowser-harness`.

You can also add the repo `skills/` folder as an [external skill directory](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills).

### OpenClaw

`~/.openclaw/openclaw.json`:

```json5
{
  skills: {
    entries: {
      "nextbrowser-harness": {
        enabled: true,
        env: { NEXTBROWSER_USE_CASE: "scrape", /* … */ },
      },
    },
  },
}
```

See [OPENCLAW.md](OPENCLAW.md) and **[AGENT_QUICKSTART.md](AGENT_QUICKSTART.md)** (script injection + per-host setup).

### Claude Code

Install: `nextbrowser agent install --host claude`

Skills load from `~/.claude/skills/` or `.claude/skills/` in the project ([docs](https://code.claude.com/docs/en/skills)).

Set env in `~/.zshrc` / `~/.bashrc` or project `.env`:

```bash
export NEXTBROWSER_USE_CASE=scrape
export NODEMAVEN_PROXY_HOST=...
```

### Cursor

Install: `nextbrowser agent install --host cursor`

Use **Cursor Settings → Rules** or `.cursor/skills/`. Env via project `.env` or Cursor secrets.

### Codex / Gemini CLI / generic shell agents

Install skill for discoverability, and export env before starting the CLI:

```bash
nextbrowser agent install --host codex   # or gemini
export NEXTBROWSER_USE_CASE=scrape
nextbrowser init --env
```

Paste `examples/agent_skill.md` or `AGENTS.md` into the agent’s system context if the host has no skills folder.

---

## Sandbox / Docker

Container must include: Python 3, this package, Playwright + Chromium, and on Linux `playwright install-deps chromium`.

---

## Quick setup script

```bash
bash scripts/setup-agent.sh    # Linux / macOS — all hosts
# scripts/setup-openclaw.ps1   # Windows
```
