# Anti-hallucination (all sites, all authenticated tasks)

External agents must not narrate success from memory. The harness enforces proof via **CLI exit codes** on every site (eBay, Reddit, LinkedIn, SaaS dashboards, etc.).

## Login (any URL)

1. `nextbrowser login <account> --url <target-site>` (+ creds + indices from `ui state` if known)
2. Read JSON: `logged_in` and `success`. If `success` is **false**, you are **not** done — stop.
3. `nextbrowser ui require-login` — **exit 0 only** means the live page looks logged in.

## Before any authenticated action (post, comment, checkout, message, form submit)

1. `nextbrowser ui require-login` → exit 0
2. Mechanical steps: `ui situation` → `ui state` → `ui click N` / `ui type N "..."` / `ui scroll` as needed
3. After submit: `nextbrowser ui verify --text "exact substring you submitted"` → **exit 0 only** means that text is visible in the live page snapshot.

If verify exits **1**, tell the user the action **did not** succeed. Do not say "verified with ui situation" unless `verify` passed.

## `ui situation` JSON

Check `agent_gates` (same fields on every site):

| Field | Meaning |
|-------|---------|
| `logged_in_verified` | `true` only when live state proves login |
| `safe_to_claim_content_posted` | `false` until `ui verify --text` exits 0 |

Default: `ui situation` **exits 1** when not logged in. Use `ui situation --permissive` only to inspect a logged-out page.

## Login inference (universal heuristics)

Uses URL + visible UI text: auth paths (`/login`, `/signin`, …), Log in + Sign up gates, sign-out / account chrome, profile URLs — not hardcoded to one domain.

## Windows

Per-account `--session` and `cmd /c` chaining apply to all `ui` / `login` calls (see `windows-cli-quirks.md`).
