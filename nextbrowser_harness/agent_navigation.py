"""Agent-facing automation — browser-use skill for UI, nextbrowser for MLX + keep-alive."""

from __future__ import annotations

# Shown in status JSON and skill — agents must follow this for tier-3 login.
AGENT_MUST_KNOW = [
    "Load the browser-use skill AND this skill. UI = browser-use only, not nextbrowser exec --action state.",
    "Before tier-3 automation: ask user which account (nextbrowser account list) or if you should add a new login.",
    "New Multilogin profile: nextbrowser account add <name> --create-mlx — verify mlx_profile_id appears in Multilogin app.",
    "Connect once: nextbrowser browser-use connect --account <name> — MLX browser stays open (keep_alive).",
    "Login flow: run the WHOLE login in ONE chain: nextbrowser browser-use chain open URL state \"input N user\" \"click M\" — never one exec/run per field.",
    "Never run browser-use close, multilogin stop-all, or nextbrowser exec --close during login — cookies save only while profile stays open.",
    "If credentials are unknown: ask the user — never use USER/PASS placeholders.",
    "When login is fully done: nextbrowser browser-use disconnect --account <name>.",
    "Read-only pages: nextbrowser scrape URL --json (no account needed).",
]


AGENT_NAVIGATION_POLICY = """
Use **browser-use** CLI for ALL UI (state / click / input) — load the **browser-use** skill.
Use **nextbrowser** for Multilogin accounts, CDP connect, chain login, scrape.

Tier 3 login (MLX + CDP) — browser MUST stay open:
  1. Ask user: which account? Or create: {cli} account add <name> --create-mlx
  2. {cli} browser-use connect --account <name>
  3. ONE chain for entire login (not separate commands per field):
     {cli} browser-use chain open "<url>" state "input 12 USER" "input 15 PASS" "click 20"
  4. When finished: {cli} browser-use disconnect --account <name>

FORBIDDEN during login: nextbrowser exec per click, browser-use close, multilogin stop-all.
FORBIDDEN always: nextbrowser exec --action state for UI, Playwright Python, placeholder credentials.

Run {cli} status — read agent_must_know and browser_use.
""".strip()


def agent_automation_guide() -> dict:
    return {
        "primary_ui": "browser-use",
        "browser_use_skill": "Required. Install: {cli} browser-use install-skill",
        "agent_must_know": AGENT_MUST_KNOW,
        "keep_alive": {
            "default_on_tier3": True,
            "why": "Multilogin saves cookies/session only while the profile browser stays open",
            "connect": "{cli} browser-use connect --account <name>",
            "login": "{cli} browser-use chain open \"<url>\" state \"input N text\" \"click M\"",
            "disconnect_when_done": "{cli} browser-use disconnect --account <name>",
        },
        "tier3_policy": {
            "mlx": True,
            "connection": "cdp",
            "account_required": True,
            "ask_user": ["which account?", "add new login?", "username/password if missing?"],
        },
        "workflow": [
            "{cli} status — read agent_must_know",
            "Install: {cli} agent install --force --with-browser-use",
            "MLX once: {cli} multilogin setup-wizard && {cli} multilogin doctor",
            "Ask user which account → {cli} account list",
            "New profile: {cli} account add <name> --create-mlx --display-name \"Label\"",
            "Connect (stays open): {cli} browser-use connect --account <name>",
            "Login in ONE chain: {cli} browser-use chain open \"<url>\" state \"input N val\" \"click M\"",
            "Done: {cli} browser-use disconnect --account <name>",
            "Scrape only: {cli} scrape \"<url>\" --json",
        ],
        "never": [
            "Separate nextbrowser exec or browser-use run per login field (closes browser)",
            "browser-use close or multilogin stop-all before disconnect",
            "nextbrowser exec --action state/click for UI",
            "Placeholder credentials (USER, PASS, empty --var)",
            "Editing ~/.nextbrowser/multilogin_tokens.yaml by hand",
        ],
    }


def agent_command_recipes() -> dict:
    guide = agent_automation_guide()
    return {
        "policy": AGENT_NAVIGATION_POLICY,
        "agent_must_know": AGENT_MUST_KNOW,
        "automation": guide,
        "account_add_mlx": '{cli} account add <name> --create-mlx --display-name "Label"',
        "account_list": "{cli} account list",
        "browser_use_connect": "{cli} browser-use connect --account <name>",
        "browser_use_chain_login": (
            '{cli} browser-use chain open "<url>" state "input 12 USER" "input 15 PASS" "click 20"'
        ),
        "browser_use_disconnect": "{cli} browser-use disconnect --account <name>",
        "browser_use_state": "{cli} browser-use run state",
        "browser_use_install_skill": "{cli} browser-use install-skill",
        "read_page": '{cli} scrape "<url>" --json',
        "mlx_setup": "{cli} multilogin setup-wizard",
        "mlx_doctor": "{cli} multilogin doctor",
    }
