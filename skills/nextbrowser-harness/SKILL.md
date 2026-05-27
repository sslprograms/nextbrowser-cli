---
name: nextbrowser-harness
description: >-
  Pairs with the browser-use skill for UI automation. nextbrowser manages Multilogin
  accounts (tier 3), connects CDP to browser-use, handles scrape/tier lookup and
  persistent sessions. **Always run `nextbrowser status` first** — `agent_must_know`
  is canonical and binding. Use `nextbrowser ui situation` (never guess login state
  or current tab). Strong user (Jake) preference for *visible mechanical steps*
  (run state/situation → read indices/refs → click/type specific index → verify).
  No simulation or placeholder actions. Immediately patch skill and/or run clean
  reinstall on version skew, profile locks, PATH issues, or stale state. Windows-first.
version: 1.7.0
license: MIT
homepage: https://github.com/sslprograms/nextbrowser-cli
user-invocable: true
compatibility: >-
  Python 3.10+. browser-use CLI + Multilogin X required for tier-3 Reddit work.
  On Windows: editable pip install -e from ~/Desktop/stan-browser; add Python
  Scripts to PATH; copy skill after changes. See clean-reinstall-procedure.md and
  references/windows-cli-quirks.md for profile locks, session conflicts, and
  "filename syntax incorrect" errors. Patch immediately on failure.
platforms:
  - macos
  - linux
  - windows
---

**New reference:** `references/windows-cli-quirks.md` — Windows-specific fixes for LOCK_PROFILE_ERROR (stop-all + disconnect + config/registry re-add with correct folder_id from `multilogin folders`), profiles_dir pointing to pytest temp (edit config.yaml to standard ~/.nextbrowser/profiles), browser-use "Session 'default' is already running with different config" (use --session <unique>, clear session.json, sequential close+command), "The filename, directory name, or volume label syntax is incorrect" (full EXE path + avoid complex shlex.join && chains on Windows; patch _bu_chain in bridge.py/login.py to use list-based or cmd /c quoting). Captures systematic-debugging patterns used this session (Phase 1 root cause on registry/config mismatch).

**Primary reference:** `references/clean-reinstall-procedure.md` (full nuke when state is inconsistent).

**Other references:** 
- `references/browser-use-bridge.md`
- `references/commands.md` 
- `references/troubleshooting.md`
- `references/multilogin.md`
- `references/automation.md`
- `references/windows-cli-quirks.md`
- `references/anti-hallucination.md` **(mandatory for any authenticated UI task)**

# Nextbrowser Harness v1.7 (Proof Gates + Anti-Hallucination + Windows CLI Edition)

**Run `nextbrowser status` first every session.** The JSON `agent_must_know` list is the single source of truth. The output below is from the current live system (May 2026).

## Canonical `agent_must_know` (EXACT from latest `nextbrowser status`)

- Use the browser-use skill for UI (state / click / type). nextbrowser handles MLX, accounts, scrape.
- Tier-3 sites (Reddit-class, hard anti-bot) require Multilogin + a named account.
- Login in ONE command: `nextbrowser login <account> --url <url>` — keeps browser open the whole time.
- To know logged-in vs logged-out, run `nextbrowser ui require-login` or `nextbrowser ui situation` — read `agent_gates.logged_in_verified` in JSON; exit 1 means NOT logged in (do not guess).
- NEVER claim content was posted/submitted unless `nextbrowser ui verify --text "<exact text>"` exits 0. Exit 1 = text is NOT on the page.
- NEVER tell the user login succeeded unless `logged_in_verified` is true in situation/require-login JSON. `login` success=false means stop.
- No account yet? Ask user the name, then it is created automatically (Multilogin profile + harness binding).
- Need credentials and don't have them? Ask the user — never use placeholder USER/PASS.
- **AI agent (next-browser + MLX):** `nextbrowser account set-credentials <name> --username U --password P` then `nextbrowser agent-run "<task>" --account <name> --url <url>` — live preflight, `sensitive_data`, auto login when logged out.
- Between manual steps: `nextbrowser ui situation` then `nextbrowser ui scroll down --pages 1` / `ui state` / `ui click N`.
- `nextbrowser agent-run` stops Multilogin when finished (default). Use `--keep-open` only if you continue manually; else `nextbrowser ui close`.
- Read-only HTML: `nextbrowser scrape "<url>" --json` (any tier, no account).
- Never: `nextbrowser exec --action state` for UI, raw Playwright Python, or `multilogin stop-all` mid-task.

**Jake/DroboAI context:** Persistent anti-detect Reddit profiles for genuine-looking promotion (comments recommending DroboAI). Use named accounts (e.g. `reddit_main`). Prioritize transparent, step-by-step mechanical UI automation over fully autonomous `agent-run` when user is monitoring. Fix blockers (LOCK_PROFILE_ERROR, PATH, version mismatch, stale session) immediately by updating this skill and/or running the clean reinstall procedure.

## Updated Command Map (v1.7 proof-gated)

| Goal | Command |
|------|---------|
| Get canonical rules + current state | `nextbrowser status` |
| Prove logged in (fail-closed) | `nextbrowser ui require-login` **(exit 0 required; checks agent_gates.logged_in_verified)** |
| Check live tab/situation (with gates) | `nextbrowser ui situation` |
| Prove submitted text on page (any action) | `nextbrowser ui verify --text "<exact text>"` **(exit 0 required)** |
| First-time / manual login | `nextbrowser login <account> --url <url>` |
| Store site login for agent | `nextbrowser account set-credentials <name> --username U --password P` |
| AI agent task (any site) | `nextbrowser agent-run "<task>" --account <name> --url <url>` |
| Follow-up mechanical UI | `nextbrowser ui state` / `ui click N` / `ui type N "text"` / `ui scroll down --pages 1` / `ui situation` |
| End session | `nextbrowser ui close` |
| Scrape | `nextbrowser scrape "<url>" --json` |
| Tier lookup | `nextbrowser tier lookup "<url>"` |
| Health checks | `nextbrowser account list` / `nextbrowser multilogin doctor` / `browser-use doctor` |

## Architecture & Pairing

- **nextbrowser**: Multilogin profile lifecycle, account registry, tiered scraping, CDP bridge, session persistence.
- **browser-use**: All UI primitives (snapshot with indexed elements `@eN` or `[N]`, click, type, vision, agent loop). Use its skill in parallel.
- Current live session (from status): Active browser-use CDP at http://127.0.0.1:63139 tied to a Multilogin profile. Some doctor warnings (cloudflared, profile_use) — address if Reddit tasks fail.

**Visible Mechanical Steps Preference:**
1. `nextbrowser ui situation` or `nextbrowser ui state` → get indexed elements.
2. Identify correct ref/index for username/password/submit/comment field.
3. `nextbrowser ui type <index> "exact text"` or `browser-use click @eX` / `type`.
4. `nextbrowser ui situation` again to verify.
5. Repeat for posting comment recommending DroboAI.

Never claim "logged in" or "posted" without running the verification command.

## Onboarding / Update Procedure (Windows)

See full details in `references/clean-reinstall-procedure.md`.

Quick update flow after changing stan-browser repo:
```bash
cd "C:\\Users\\jakek\\Desktop\\stan-browser"
pip install -e ".[playwright,undetected]"
export PATH="$PATH:/c/Users/jakek/AppData/Roaming/Python/Python312/Scripts"
cp -r skills/nextbrowser-harness "C:/Users/jakek/AppData/Local/hermes/skills/"
nextbrowser init --env
nextbrowser status
```

Add the Scripts path to your permanent environment for convenience.

Run `nextbrowser multilogin setup-wizard` if MLX tokens/profiles need refresh (interactive).

## Troubleshooting

- **Profile lock / stale session:** Run clean reinstall procedure.
- **nextbrowser not found:** Export PATH or use full path to the Scripts dir.
- **browser-use doctor warnings:** Follow its install hints (cloudflared, profile update).
- **Version skew between skill and package:** The bundled skill in stan-browser/skill_pack and hermes copy must stay in sync. Update both.
- Any failure: Patch this SKILL.md immediately with new rules from `nextbrowser status`.

## Verify

```bash
nextbrowser status
nextbrowser ui situation
nextbrowser account list
nextbrowser multilogin doctor
browser-use doctor
```

After any change to CLI code or this skill, re-run status, verify the `agent_must_know` list matches what is documented here, and patch this file if it has diverged.

This skill is kept in sync with https://github.com/sslprograms/nextbrowser-cli (local clone at ~/Desktop/stan-browser).
