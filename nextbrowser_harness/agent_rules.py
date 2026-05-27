"""
Single source of truth for agent guidance — referenced by status JSON, SKILL.md, CLI output.

Maps directly to Nextbrowser Harness MVP v1.3 spec:
  - Four-layer stack (browser / proxy / automation / captcha)
  - Two use cases: account automation, tiered scraping
  - Browser-use is the default automation framework; UI commands run through it.

Edit this file (not the skill copies) to change agent behavior everywhere.
"""

from __future__ import annotations

VERSION = "1.3"


MUST_KNOW = [
    "Use the browser-use skill for UI (state / click / type). nextbrowser handles MLX, accounts, scrape.",
    "Tier-3 sites (Reddit-class, hard anti-bot) require Multilogin + a named account.",
    "Login in ONE command: `{cli} login <account> --url <url>` — keeps browser open the whole time.",
    "To know logged-in vs logged-out and what tab is visible, run `{cli} ui situation` (reads live CDP + browser-use state — do not guess).",
    "No account yet? Ask user the name, then it is created automatically (Multilogin profile + harness binding).",
    "Need credentials and don't have them? Ask the user — never use placeholder USER/PASS.",
    "Feed/social tasks (Reddit comments, scroll to post): use `{cli} agent-run \"<task>\" --account <name> --url <url>` — agent can scroll/click/type like next-browser.",
    "Between manual steps: `{cli} ui situation` then `{cli} ui scroll down --pages 1` / `ui state` / `ui click N`.",
    "`{cli} agent-run` stops Multilogin when finished (default). Use `--keep-open` only if you continue manually; else `{cli} ui close`.",
    "Read-only HTML: `{cli} scrape \"<url>\" --json` (any tier, no account).",
    "Never: `nextbrowser exec --action state` for UI, raw Playwright Python, or `multilogin stop-all` mid-task.",
]


POLICY = """
Read `{cli} status` first — `agent_must_know` + `commands` show the canonical workflow.

Use cases (from MVP spec):
  1. Account automation — persistent MLX profiles, sticky IPs, multi-account.
     Login:    {cli} login <name> --url <url>
     Drive:    {cli} ui open / state / click N / type N text / close
  2. Scraping — three tiers, auto-escalation.
     {cli} scrape "<url>" --json
     {cli} tier lookup "<url>"

UI is always browser-use (CDP). nextbrowser owns Multilogin profile lifecycle so the
browser stays open between commands — never close the profile until the task is done.
""".strip()


def automation_guide() -> dict:
    """Structured guide returned in `status` JSON. {cli} placeholder replaced by harness."""
    return {
        "version": VERSION,
        "stack": {
            "browser": ["native", "multilogin", "gologin", "octo"],
            "proxy": ["nodemaven", "custom", "none"],
            "automation": ["browser_use", "playwright"],
            "captcha": "optional (off by default)",
        },
        "use_cases": {
            "accounts": {
                "login": "{cli} login <account> --url <url>",
                "ui": "{cli} ui state | click N | type N \"text\" | close",
                "list": "{cli} account list",
                "add": "{cli} account add <name> --create-mlx",
            },
            "scrape": {
                "fetch": '{cli} scrape "<url>" --json',
                "tier_lookup": '{cli} tier lookup "<url>"',
                "tiers": {
                    "1": "HTTP only — APIs, static HTML",
                    "2": "Headless browser — most modern sites",
                    "3": "Headful + Multilogin + residential proxy — hard anti-bot",
                },
            },
        },
        "must_know": MUST_KNOW,
        "ask_user_before": [
            "Which account to use (or whether to add a new login)",
            "Username / password if credentials missing",
        ],
        "never": [
            "nextbrowser exec --action state/click for UI (use {cli} ui or browser-use)",
            "Separate exec/run per field during login (use one `login` command)",
            "browser-use close / multilogin stop-all before the task is done",
            "Raw Playwright Python for browser control",
            "Editing ~/.nextbrowser/multilogin_tokens.yaml by hand",
        ],
    }


def command_recipes() -> dict:
    """Flat command templates. {cli} is replaced at runtime."""
    return {
        "policy": POLICY,
        "agent_must_know": MUST_KNOW,
        "automation": automation_guide(),
        "login": "{cli} login <account> --url <url>",
        "login_with_creds": '{cli} login <account> --url <url> --username U --password P',
        "agent_run": '{cli} agent-run "<task>" --account <name>',
        "agent_run_with_url": '{cli} agent-run "<task>" --account <name> --url <url>',
        "ui_open": '{cli} ui open "<url>"',
        "ui_situation": "{cli} ui situation",
        "ui_state": "{cli} ui state",
        "ui_click": "{cli} ui click N",
        "ui_scroll": "{cli} ui scroll down --pages 1",
        "ui_type": '{cli} ui type N "text"',
        "ui_close": "{cli} ui close",
        "agent_run_keep_open": '{cli} agent-run "<task>" --account <name> --keep-open',
        "scrape": '{cli} scrape "<url>" --json',
        "tier_lookup": '{cli} tier lookup "<url>"',
        "account_list": "{cli} account list",
        "account_add": "{cli} account add <name> --create-mlx",
        "mlx_setup": "{cli} multilogin setup-wizard",
        "mlx_doctor": "{cli} multilogin doctor",
        "install_skill": "{cli} agent install --force --with-browser-use",
    }


def render(cli_prefix: str) -> dict:
    """Replace {cli} placeholders in must_know + recipes for status JSON."""

    def sub(value):
        if isinstance(value, str):
            return value.replace("{cli}", cli_prefix)
        if isinstance(value, list):
            return [sub(v) for v in value]
        if isinstance(value, dict):
            return {k: sub(v) for k, v in value.items()}
        return value

    return {
        "must_know": [line.replace("{cli}", cli_prefix) for line in MUST_KNOW],
        "policy": POLICY.replace("{cli}", cli_prefix),
        "guide": sub(automation_guide()),
        "commands": sub(command_recipes()),
    }
