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

If verify exits **1**, tell the user the action **did not** succeed. Do not say "verified" unless `verify` passed.

## AI agent-run (next-browser style)

To make the **AI agent** actually log in (instead of stopping at a login wall):

1. `nextbrowser account set-credentials <account> --username U --password P`
2. `nextbrowser agent-run "<task>" --account <account> --url <url> --login-url <login-page>`

This injects browser-use `sensitive_data` so the LLM never sees the secret values, but can still complete login.

