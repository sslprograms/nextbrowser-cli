"""Agent-facing automation — browser-use skill for UI, nextbrowser for MLX accounts + CDP."""

from __future__ import annotations

AGENT_NAVIGATION_POLICY = """
Use **browser-use** CLI for all UI automation (state / click / input) — load the browser-use skill.
Use **nextbrowser** for Multilogin accounts, CDP connect, scrape, and tier lookup.

Tier 3 flow:
  1. Ask user which account (or create: nextbrowser account add <name> --create-mlx)
  2. {cli} browser-use connect --account <name>   # starts MLX, saves CDP
  3. browser-use --cdp-url <cdp> open "<url>" && browser-use --cdp-url <cdp> state
  4. browser-use click N / input N "text"  (indices from state)
  Or shorthand: {cli} browser-use run state  (CDP injected from connect)

Do NOT use nextbrowser exec state/click for UI — use browser-use.
Do NOT write Playwright Python.
Ask user for credentials when login is needed and unknown.
""".strip()


def agent_automation_guide() -> dict:
    return {
        "primary_ui": "browser-use",
        "browser_use_skill": "Install: nextbrowser browser-use install-skill (or load browser-use skill)",
        "tier3_policy": {
            "mlx": True,
            "connection": "cdp",
            "connect": "{cli} browser-use connect --account <name>",
            "ui_commands": "browser-use state | click N | input N \"text\"",
        },
        "workflow": [
            "Install skills: `{cli} agent install --force --with-browser-use`",
            "MLX once: `{cli} multilogin setup-wizard`",
            "Ask user: which account? `{cli} account list`",
            "New login: `{cli} account add <name> --create-mlx`",
            "Connect CDP: `{cli} browser-use connect --account <name>`",
            "UI loop: `browser-use --cdp-url <cdp> open URL` → `state` → `click` / `input`",
            "Or: `{cli} browser-use run state` (uses saved CDP from connect)",
            "Read-only: `{cli} scrape URL --json`",
            "Ask user for credentials before login if unknown.",
        ],
        "never": [
            "Do not use nextbrowser exec --action state for UI (use browser-use)",
            "Do not guess credentials",
            "Do not edit multilogin_tokens.yaml by hand",
        ],
    }


def agent_command_recipes() -> dict:
    guide = agent_automation_guide()
    return {
        "policy": AGENT_NAVIGATION_POLICY,
        "automation": guide,
        "browser_use_connect": "{cli} browser-use connect --account <name>",
        "browser_use_state": "{cli} browser-use run state",
        "browser_use_open": "{cli} browser-use run open <url>",
        "browser_use_install_skill": "{cli} browser-use install-skill",
        "account_list": "{cli} account list",
        "account_add": "{cli} account add <name> --create-mlx",
        "read_page": "{cli} scrape \"<url>\" --json",
        "mlx_setup": "{cli} multilogin setup-wizard",
        "mlx_doctor": "{cli} multilogin doctor",
    }
