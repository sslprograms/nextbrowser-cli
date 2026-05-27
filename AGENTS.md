# Agent instructions

Run `nextbrowser status` first. `agent_must_know` in the JSON is canonical.

## Spec — Nextbrowser Harness MVP v1.3

Multimodular browser harness. Two use cases:

1. **Account automation** — Multilogin profile per account, CDP, sticky proxy.
2. **Scraping** — three tiers, auto-escalation, no account for tier 1–2.

## Rules

1. Load **browser-use** skill + this skill.
2. Ask user: account name / new login / credentials when missing.
3. **Manual login**: `nextbrowser login <name> --url <url>` (auto-creates account if needed).
4. **AI agent task**: `nextbrowser agent-run "<task>" --account <name>` (fully autonomous).
5. **Follow-up actions**: `nextbrowser ui state | click N | type N "text" | eval "..."`.
6. **End task**: `nextbrowser ui close`.
7. **Scrape only**: `nextbrowser scrape "<url>" --json`.

## Never

- `nextbrowser exec --action state/click` for UI (deprecated path).
- Separate `exec`/`run` per login field — use `login`.
- `browser-use close` / `multilogin stop-all` before `ui close`.
- Raw Playwright Python for navigation.
- Placeholder credentials.

Skill: `skills/nextbrowser-harness/SKILL.md`
