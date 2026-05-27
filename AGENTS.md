# Agent instructions

Run `nextbrowser status` first. `agent_must_know` in the JSON is canonical.

## Spec — Nextbrowser Harness MVP v1.3

Multimodular browser harness. Two use cases:

1. **Account automation** — Multilogin profile per account, CDP, sticky proxy.
2. **Scraping** — three tiers, auto-escalation, no account for tier 1–2.

## Rules

1. **MLX + raw CDP** — no browser-use, no indexed shortcuts. `nextbrowser connect --account <name>` → `nextbrowser cdp send <Domain.method> --params '<json>'`. See `references/cdp-agent.md`.
2. Ask user: account name / new login / credentials when missing.
3. **Manual login**: `nextbrowser login <name> --url <url>` (auto-creates account if needed).
4. **You are the agent** — every observe/act = `cdp send` (Page, DOM, Input, Runtime, …). Prove with CDP reads before claiming success.
5. **Proof before claims**: e.g. `cdp send Runtime.evaluate` with an expression that checks visible text / URL. Exit 0 on `cdp send` only means the CDP call succeeded — you must interpret the JSON result.
6. **Legacy** `ui state` / `ui click` exist but do not use them for account automation.
7. **End task**: `nextbrowser ui close`.
8. **Scrape only**: `nextbrowser scrape "<url>" --json`.

## Never

- `nextbrowser exec --action state/click` for UI (deprecated path).
- Separate `exec`/`run` per login field — use `login`.
- `multilogin stop-all` before `ui close` / `disconnect`.
- Raw Playwright Python for navigation.
- Placeholder credentials.
- Telling the user you logged in or posted when `require-login` / `verify` failed or was skipped.

Skill: `skills/nextbrowser-harness/SKILL.md` — install for any host: `nextbrowser agent install --host all --force`. See `references/anti-hallucination.md`
