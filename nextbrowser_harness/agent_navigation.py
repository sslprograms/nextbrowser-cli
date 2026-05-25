"""Agent-facing automation API — tier 3 = Multilogin account + CDP + user prompts."""

from __future__ import annotations

AGENT_NAVIGATION_POLICY = """
Use the nextbrowser CLI only (see platform.cli from `nextbrowser status`). Do NOT write Playwright/Puppeteer Python unless the user asks.

Tier 3 browser automation (exec / browse when tier is 3):
  - Requires a **named Multilogin account** (--account or --profile). Browser connects over **CDP** to an MLX profile.
  - Before the first run: ask **Which account should I use?** or **Should I add a new login?**
  - New login: `account add <name> --create-mlx` → one-time login via exec (state/click/type) → cookies persist in MLX.
  - If you need username/password and do not have them: **ask the user** — never guess or use placeholders.

Indexed UI flow (after account is chosen):
  1. {cli} exec "<url>" --account <name> --action goto --action state
  2. Read [N] from JSON `state` → detail
  3. {cli} exec "<url>" --account <name> --action "type:N|value" --action "click:N"
  4. Re-run `state` after navigation

Read-only (no MLX account): {cli} scrape "<url>" --json` (any tier, no browser)
""".strip()


def agent_automation_guide() -> dict:
    """Single machine-readable guide — returned in `nextbrowser status`."""
    return {
        "tier3_policy": {
            "required": True,
            "browser": "multilogin",
            "connection": "cdp",
            "account_flag": "--account <name> (alias: --profile)",
            "ask_user_before_automate": [
                "Which saved account should I use? (account list)",
                "Or should I create a new login? (account add <name> --create-mlx)",
            ],
            "ask_user_for_credentials_when": [
                "Recipe or actions need login and username/password are missing or placeholders",
            ],
        },
        "workflow": [
            "Run `{cli} status` — read `accounts`, `how_to_automate`, `platform.cli`.",
            "MLX once: `{cli} multilogin setup-wizard` and `{cli} multilogin doctor`.",
            "List accounts: `{cli} account list`.",
            "New account: `{cli} account add <name> --create-mlx --site reddit.com`.",
            "Ask user which account (or new login) before tier-3 exec.",
            "If login needed and credentials unknown: ask user for username/password.",
            "Automate: `{cli} exec \"<url>\" --account <name> --action goto --action state`.",
            "Use indices from `state`: `--action \"type:N|text\"` `--action \"click:N\"`.",
            "Re-run `state` after navigation. Connection stays CDP via Multilogin.",
            "Read-only: `{cli} scrape \"<url>\" --json` (no account required).",
        ],
        "element_search": {
            "default": "indexed",
            "indexed": "state → pick N → click:N / type:N|value (CDP session)",
            "playwright": "CSS only when selectors are known",
        },
        "commands": {
            "status": "{cli} status",
            "account_list": "{cli} account list",
            "account_add": "{cli} account add <name> --create-mlx",
            "exec": '{cli} exec "<url>" --account <name> --action goto --action state',
            "scrape": '{cli} scrape "<url>" --json',
        },
        "never": [
            "Do not run tier-3 exec without --account <registered_name>.",
            "Do not invent Playwright/Python browser scripts.",
            "Do not guess login credentials — ask the user.",
            "Do not edit ~/.nextbrowser/multilogin_tokens.yaml by hand.",
        ],
    }


def agent_command_recipes() -> dict:
    guide = agent_automation_guide()
    return {
        "policy": AGENT_NAVIGATION_POLICY,
        "automation": guide,
        "account_list": "{cli} account list",
        "account_add_mlx": "{cli} account add <name> --create-mlx --display-name \"My Site\"",
        "read_page": "{cli} scrape \"<url>\" --json",
        "open_and_list_elements": '{cli} exec "<url>" --account <name> --action goto --action state',
        "click_by_index": '{cli} exec "<url>" --account <name> --action "click:INDEX"',
        "type_by_index": '{cli} exec "<url>" --account <name> --action "type:INDEX|VALUE"',
        "login_recipe": (
            '{cli} exec "<url>" --account <name> --recipe site.com/login '
            '--var username=FROM_USER --var password=FROM_USER'
        ),
        "mlx_setup": "{cli} multilogin setup-wizard",
        "mlx_doctor": "{cli} multilogin doctor",
        "install_skill": "{cli} agent install --force",
        "action_prefixes": [
            "state",
            "find:",
            "type:",
            "fill:",
            "click:",
            "wait-for:",
            "eval:",
            "goto",
            "logged-in",
        ],
    }
