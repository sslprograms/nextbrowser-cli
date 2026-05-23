# Troubleshooting (agents)

## CLI not found

Run `nextbrowser status` and use the full `platform.cli` string (often `python -m nextbrowser_harness.cli`).

Ensure venv is activated or `nextbrowser` is on PATH after `pip install -e .`.

## Skill not loading (Hermes / OpenClaw / Cursor)

```bash
nextbrowser agent doctor
nextbrowser agent install --host all --force
```

| Host | Check path |
|------|------------|
| Hermes | `~/.hermes/skills/browser-automation/nextbrowser-harness/SKILL.md` |
| OpenClaw | `~/.openclaw/skills/nextbrowser-harness/SKILL.md` |
| Claude | `~/.claude/skills/nextbrowser-harness/SKILL.md` |
| Cursor | `~/.cursor/skills/nextbrowser-harness/SKILL.md` |

Hermes: start a new session or run `/nextbrowser-harness` after install.

OpenClaw: new session after install; set env in `openclaw.json` → `skills.entries.nextbrowser-harness.env`.

## Invalid SKILL.md / YAML errors

Frontmatter must be valid YAML. Run:

```bash
python -m pytest tests/test_skill_pack.py -q
```

## Playwright missing

```bash
pip install -e ".[playwright]"
playwright install chromium
# Linux may also need:
playwright install-deps chromium
```

## Account run / exec fails

Set `NEXTBROWSER_AUTOMATION=playwright` in env or `~/.nextbrowser/config.yaml`.

## MLX issues

| Symptom | Fix |
|---------|-----|
| Signin 400 | Use MLX app login credentials |
| Token 400 | Run `multilogin automation-token` after signin |
| Profile already running | Harness reuses CDP; or `multilogin stop-all` |
| Launcher 404 on stop | Use `multilogin stop-all` |

## Agent wrote Playwright Python instead of CLI

Reload skill. Policy: use `nextbrowser exec` / `browse` / `scrape` only. See `AGENTS.md` in repo root.

## Sandboxed agents

The sandbox image must include Python, this package, Playwright, and Chromium — not just the host OS.
