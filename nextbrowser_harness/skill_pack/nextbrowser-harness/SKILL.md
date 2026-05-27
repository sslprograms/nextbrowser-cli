---
name: nextbrowser-harness
description: >-
  Multilogin X + raw Chrome DevTools Protocol (CDP). Any AgentSkills host drives MLX
  via `nextbrowser cdp send` — no indexed click shortcuts, no browser-use API key.
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

**Not used:** browser-use, indexed `ui click N` shortcuts (legacy only).

## Control loop

```bash
nextbrowser status
nextbrowser connect --account <name>
nextbrowser cdp session
nextbrowser cdp send Page.navigate --params '{"url":"https://example.com"}'
nextbrowser cdp send DOM.getDocument --params '{"depth":-1,"pierce":true}'
nextbrowser cdp send Runtime.evaluate --params '{"expression":"document.title","returnByValue":true}'
nextbrowser disconnect --account <name>
```

```bash
nextbrowser cdp catalog   # example methods
```

## Rules

1. **Every** action and observation = `cdp send` (no `ui click` / `ui type` for automation).
2. Read JSON output after each send; pick `nodeId`, coordinates, etc. for the next send.
3. Prove success with CDP (Runtime.evaluate / DOM) before telling the user something worked.
4. `nextbrowser multilogin doctor` if MLX won't start.

## References

- `references/cdp-agent.md` — CDP recipes
- `references/agent-host-drives-browser.md`
- `references/anti-hallucination.md`
