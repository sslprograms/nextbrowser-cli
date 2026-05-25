# Scripts

| Script | Platform | Purpose |
|--------|----------|---------|
| `setup-agent.sh` | Linux / macOS | venv, Playwright, install skills for all agent hosts |
| `setup-multilogin.sh` | Linux / macOS | Delegates to `nextbrowser multilogin setup-wizard` |
| `setup-multilogin.ps1` | Windows | Same as `setup-multilogin.sh` |
| `setup-openclaw.sh` | Linux / macOS | OpenClaw-only quick setup (see also `setup-agent.sh`) |
| `setup-openclaw.ps1` | Windows | Install package + all agent skills |
| `sync_skill_pack.py` | Any | Copy `skills/` → `nextbrowser_harness/skill_pack/` (run before release) |

Run tests: `python -m pytest tests/ -q` from repo root.
