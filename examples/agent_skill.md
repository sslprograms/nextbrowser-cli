# Nextbrowser Harness — Agent Skill Snippet (Linux / macOS / Windows)

Install once, then the agent can drive the harness via CLI (JSON-friendly).

For OpenClaw, prefer the bundled skill: `nextbrowser openclaw install` (see docs/OPENCLAW.md).

## Install

```bash
pip install -e /path/to/stan-browser
pip install -e "/path/to/stan-browser[playwright]"
playwright install chromium
```

## Bootstrap (60s headless)

```bash
export NEXTBROWSER_USE_CASE=scrape
export NEXTBROWSER_PROXY=nodemaven
export NODEMAVEN_PROXY_HOST=gate.nodemaven.com:8080
export NODEMAVEN_PROXY_USER=...
export NODEMAVEN_PROXY_PASSWORD=...
nextbrowser init --env
```

## Scrape

```bash
nextbrowser scrape "https://example.com/page" --json
nextbrowser tier lookup "https://reddit.com/r/test"
```

## Multi-account

```bash
nextbrowser account add social_01 --notes "Twitter portfolio"
nextbrowser account run social_01 "Check inbox and summarize unread DMs" --url https://...
```

## Use case selection

- `scrape` — tiered web scraping, cost-efficient by default
- `accounts` — persistent profiles, sticky IPs, parallel account orchestration

LLM: uses the host agent's configured model; no extra API key step at install.
