---
name: nextbrowser-harness
description: >-
  Multilogin X + raw Chrome DevTools Protocol (CDP). Any AgentSkills host drives MLX
  via `nextbrowser cdp send` — no indexed click shortcuts, no extra API key.
version: 2.1.0
license: MIT
user-invocable: true
compatibility: >-
  Python 3.10+, Multilogin X, pip install -e ".[playwright]" && playwright install chromium.
platforms:
  - macos
  - linux
  - windows
---

# Multilogin X + raw CDP (no shortcuts)

For **any AgentSkills host** (Cursor, Claude Code, Hermes, OpenClaw, …). You issue **explicit CDP methods**; the harness forwards them to the MLX browser over CDP.

## Install

```bash
pip install -e ".[playwright]"
playwright install chromium
nextbrowser multilogin setup-wizard
nextbrowser agent install --host all --force
```

## Stack

| Piece | Role |
|-------|------|
| **Multilogin X** | Browser + proxy; launcher returns **CDP URL** |
| **You (host agent)** | `cdp send Page.*` / `DOM.*` / `Input.*` / `Runtime.*` |
| **nextbrowser** | Starts MLX, attaches CDP session, returns JSON results |

**Never use (CLI returns error):** `ui`, `ui close`, `state`, `click`, `type`, indexed shortcuts.

## Control loop

```bash
nextbrowser connect --account <name>
nextbrowser cdp navigate --account <name> "https://example.com"
nextbrowser cdp send --account <name> <Domain.method> --params '<json>'
nextbrowser disconnect --account <name>
```

```bash
nextbrowser cdp catalog   # example methods
```

## Login (deterministic)

```bash
nextbrowser account set-credentials <name> --username "U" --password "P"
nextbrowser login <name> --url "https://site.com/login"
```

Finds the form, types credentials with trusted CDP `Input` events, submits, and verifies —
returns `logged_in` + before/after screenshots. Use this instead of hand-building login clicks.

## Rules

1. **Every** command includes `--account <name>`. Connect does not save a session file unless `--persist-session`.
2. **New page** → `cdp survey --account <name>` before any action. Each segment has `visible_text` + **`screenshot_path`** (PNG). **Open every screenshot with your vision model** — snapshots are how you understand layout.
3. After important actions → `cdp snapshot --account <name>` to verify visually.
4. Only after survey + snapshots → `cdp send` for clicks/types.
5. Read JSON after each send; use coordinates from survey snapshots + `interactive[]`.
6. Prove success with **snapshot +** CDP (Runtime.evaluate) before telling the user something worked.
7. `nextbrowser multilogin doctor` if MLX won't start.

## References

- `references/cdp-agent.md` — CDP recipes
- `references/agent-host-drives-browser.md`
- `references/anti-hallucination.md`
- `references/commands.md` · `references/troubleshooting.md` · `references/multilogin.md`
