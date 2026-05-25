# Agent instructions

**UI = browser-use skill.** **MLX/accounts = nextbrowser.**

```bash
nextbrowser agent install --force --with-browser-use
nextbrowser browser-use connect --account <name>
nextbrowser browser-use run state
browser-use click 5   # or: nextbrowser browser-use run click 5
```

Read-only: `nextbrowser scrape URL --json`

See `skills/nextbrowser-harness/SKILL.md`.
