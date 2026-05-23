# Nextbrowser Harness — Agent Skill Snippet

AgentSkills-compatible skill: `skills/nextbrowser-harness/SKILL.md`

Install for your host:

```bash
nextbrowser agent install --host hermes --force    # ~/.hermes/skills/browser-automation/...
nextbrowser agent install --host openclaw --force
nextbrowser agent install --host all --force
nextbrowser agent doctor
```

**Policy:** Use `nextbrowser exec` / `browse` / `scrape` — do not write standalone Playwright Python.

## Bootstrap

```bash
pip install -e ".[playwright]"
playwright install chromium
export NEXTBROWSER_USE_CASE=scrape
export NEXTBROWSER_AUTOMATION=playwright
nextbrowser init --env
```

## Examples

```bash
nextbrowser status
nextbrowser scrape "https://example.com"
nextbrowser exec "https://example.com" --js "document.title"
nextbrowser exec "https://www.reddit.com" --steps-file examples/steps-reddit.json
```

See `docs/AGENT_QUICKSTART.md` for full host setup (Hermes, OpenClaw, Claude, Cursor).
