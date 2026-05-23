# Nextbrowser Harness (MVP v1.2)

Python 3 multimodular browser automation harness for AI agents. Implements the **Nextbrowser_Harness_MVP_v1.2** spec: scrape data or manage accounts, with a four-layer stack (browser → proxy → automation → optional CAPTCHA) and a three-tier scraping model.

**Official CLI repository:** [github.com/sslprograms/nextbrowser-cli](https://github.com/sslprograms/nextbrowser-cli)

The `nextbrowser` command is provided by this package (`nextbrowser-harness` on PyPI name; repo folder `nextbrowser-cli`).

## Install (Linux / macOS / Windows)

**From GitHub (canonical):**

```bash
git clone https://github.com/sslprograms/nextbrowser-cli.git
cd nextbrowser-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[playwright]"
playwright install chromium
playwright install-deps chromium   # Linux only
```

**Or from an existing clone** (e.g. `stan-browser` on your machine):

```powershell
# Windows
python -m venv .venv; .venv\Scripts\activate
pip install -e ".[playwright]"
playwright install chromium
```

## Onboarding (< 5 minutes)

```bash
nextbrowser init
nextbrowser init --env   # OpenClaw / agents
```

Config: `~/.nextbrowser/config.yaml` (all platforms) or `.nextbrowser.yaml` in cwd.

## Commands

| Command | Description |
|---------|-------------|
| `nextbrowser init` | Interactive onboarding (2 questions + proxy choice) |
| `nextbrowser init --env` | Agent-friendly onboarding from env vars |
| `nextbrowser status` | Show stack configuration |
| `nextbrowser scrape <url>` | Tier DB lookup → auto-escalate 1→2→3 |
| `nextbrowser scrape <url> --tier 2` | Force tier |
| `nextbrowser tier lookup <url>` | Show recommended tier |
| `nextbrowser tier set <domain> <1\|2\|3>` | User override |
| `nextbrowser agent install --host <id>` | Install skill (hermes, openclaw, claude, cursor, all, …) |
| `nextbrowser agent doctor` | Verify CLI + paths for all agent hosts |
| `nextbrowser exec <url> --js "..."` | **Inject JS** / automate (agents, OpenClaw) |
| `nextbrowser exec <url> --steps-file steps.json` | Multi-step script file |
| `nextbrowser browse <url>` | Browse with optional `--js`, `--action`, MLX |
| `nextbrowser account add <id>` | Register isolated account profile |
| `nextbrowser account run <id> "eval:..."` | Run task or JS for one account |
| `nextbrowser multilogin profiles` | List MLX profile UUIDs |
| `nextbrowser multilogin stop-all` | Stop all MLX launcher profiles |

## Four-layer stack (MVP)

| Layer | Options | Default |
|-------|---------|---------|
| Browser | native, **Multilogin X API**, GoLogin, Octo | Native (Playwright Chromium) |
| Proxy | NodeMaven residential, BYO | NodeMaven |
| Automation | Browser Use, Playwright | Browser Use (falls back to Playwright) |
| LLM | Inherits agent runtime | No separate key at install |
| CAPTCHA | 2Captcha / CapMonster token | Off |

## Scraping tiers

| Tier | Method | Cost |
|------|--------|------|
| 1 | Direct HTTP (`requests`) | Lowest |
| 2 | Headless browser + JS | Moderate |
| 3 | Headful anti-detect + residential proxy | Highest |

Domain recommendations ship in `nextbrowser_harness/tiers/database.json`. Failed scrapes escalate automatically; successful tier is cached locally.

## Account automation

Each account gets:

- Its own browser profile directory under `~/.nextbrowser/profiles/`
- Sticky proxy session (NodeMaven username suffix)
- Persistent registry in `accounts.json` — no re-login every run by design

## Project layout

```
nextbrowser_harness/
  cli.py              # CLI entry
  harness.py          # Orchestrator
  onboarding.py
  config.py
  tiers/              # Curated tier DB + resolver
  layers/             # browser, proxy, automation, captcha
  workflows/          # scraping, accounts
examples/
  agent_skill.md      # Snippet for OpenClaude / Claude skills
tests/
```

## Multilogin X

Uses the [Multilogin X API](https://documenter.getpostman.com/view/28533318/2s946h9Cv9). You need:

1. **Multilogin X** installed with the local **launcher/agent** running
2. **Auth** — one of:
   - `MULTILOGIN_AUTOMATION_TOKEN` (best for automation; fetch via CLI below)
   - `MULTILOGIN_EMAIL` + `MULTILOGIN_PASSWORD`
   - `nextbrowser multilogin signin` then `nextbrowser multilogin automation-token`
3. **Profile UUIDs** — `MULTILOGIN_FOLDER_ID` + `MULTILOGIN_PROFILE_ID` (or per-account `MULTILOGIN_PROFILE_<ACCOUNT>`)

```powershell
nextbrowser multilogin signin
nextbrowser multilogin automation-token
nextbrowser multilogin folders
nextbrowser init   # choose browser: Multilogin (option 2)
```

Start/stop manually:

```powershell
nextbrowser multilogin start <profile-uuid> --folder-id <folder-uuid>
nextbrowser multilogin stop <profile-uuid>
```

With `browser: multilogin` in config, tier 2/3 scraping and `account run` launch MLX profiles and attach Playwright over CDP (`automation_type=playwright`).

## AI agents (Hermes, OpenClaw, Claude Code, Cursor, Continue, Roo, …)

```bash
nextbrowser agent list-hosts
nextbrowser agent install --host all --force
nextbrowser agent doctor
```

Skills follow the [AgentSkills](https://agentskills.io/) format (`SKILL.md` + YAML frontmatter). Hermes uses category layout: `~/.hermes/skills/browser-automation/nextbrowser-harness/`.

**[docs/AGENT_QUICKSTART.md](docs/AGENT_QUICKSTART.md)** · **[docs/AGENT_HOSTS.md](docs/AGENT_HOSTS.md)** · OpenClaw: **[docs/OPENCLAW.md](docs/OPENCLAW.md)**

## Tests

```powershell
pip install -e ".[dev]"
python -m pytest -m "not integration"
python -m pytest  # includes live httpbin tier-1 test
```

## Open source note

Per the spec, this MVP is structured for GitHub distribution: modular layers, community tier DB contributions, and NodeMaven as the default proxy sponsor — not a hard lock-in.

Reference: `Nextbrowser_Harness_MVP_v1.2_1.docx`
