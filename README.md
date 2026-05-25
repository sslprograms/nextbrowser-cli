# Nextbrowser Harness (MVP v1.2)

Python 3 multimodular browser automation harness for AI agents: tiered scraping, browser automation, Multilogin X, and AgentSkills for Hermes, OpenClaw, Claude Code, Cursor, and more.

**Repository:** [github.com/sslprograms/nextbrowser-cli](https://github.com/sslprograms/nextbrowser-cli)

## Install

```bash
git clone https://github.com/sslprograms/nextbrowser-cli.git
cd nextbrowser-cli
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[playwright,undetected]"
playwright install chromium
playwright install-deps chromium   # Linux only
```

On headless Linux, install `xvfb` for Multilogin X and undetected Chrome: `sudo apt install xvfb`.

## Quick start

```bash
nextbrowser init --env
nextbrowser status
nextbrowser scrape "https://example.com"
nextbrowser agent install --host all --force
```

Config: `~/.nextbrowser/config.yaml` or `.nextbrowser.yaml` in the project directory.

Native browser uses undetected Chrome by default (`NEXTBROWSER_DRIVER=undetected`). Set `NEXTBROWSER_DRIVER=playwright` for bundled Chromium. Proxy defaults to `none`; NodeMaven is optional for tier-3 native scraping.

## Commands

| Command | Description |
|---------|-------------|
| `nextbrowser init` / `init --env` | Onboarding (interactive or from env) |
| `nextbrowser status` | Config + `platform.cli` + agent navigation recipes |
| `nextbrowser scrape <url>` | Tiered HTTP / browser fetch |
| `nextbrowser exec <url>` | Browser automation, JS inject, step files |
| `nextbrowser browse <url>` | Same engine as `exec` (Reddit-oriented defaults) |
| `nextbrowser account add/run` | Persistent profiles per account |
| `nextbrowser multilogin *` | MLX setup-wizard, sign-in, profiles, doctor |
| `nextbrowser agent install` | Install `SKILL.md` for agent hosts |

## Multilogin X

Recommended: `nextbrowser multilogin setup-wizard` (email in `.env`, password never saved).

| OS | Script (calls setup-wizard) |
|----|--------|
| Windows | `.\scripts\setup-multilogin.ps1` |
| Linux / macOS | `./scripts/setup-multilogin.sh` |

Then: `nextbrowser multilogin doctor` and `nextbrowser exec <url> --browser multilogin --profile default`.

## AI agents

Skills: [AgentSkills](https://agentskills.io/) format in `skills/nextbrowser-harness/`.

```bash
nextbrowser agent install --host all --force
nextbrowser agent doctor
```

Docs: [docs/AGENT_QUICKSTART.md](docs/AGENT_QUICKSTART.md) · [docs/AGENT_HOSTS.md](docs/AGENT_HOSTS.md) · [docs/OPENCLAW.md](docs/OPENCLAW.md)

## Project layout

```
nextbrowser_harness/     # Python package (CLI, layers, workflows, MLX)
skills/nextbrowser-harness/   # Agent skill (source of truth)
nextbrowser_harness/skill_pack/   # Bundled copy for pip installs (run scripts/sync_skill_pack.py)
examples/                # steps JSON, JS snippets
docs/                    # Agent and OpenClaw guides
scripts/                 # Setup helpers (see scripts/README.md)
tests/
```

## Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

## Before you push to GitHub

- Do **not** commit `.env`, tokens, or screenshots (see [SECURITY.md](SECURITY.md))
- Run `python scripts/sync_skill_pack.py` after editing `skills/`
- Run `python -m pytest tests/ -q`
- Confirm `git status` shows no `.env`, `*.egg-info`, or `.nextbrowser/`

## License

MIT — see [LICENSE](LICENSE).
