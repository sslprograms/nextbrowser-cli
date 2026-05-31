"""
Single source of truth for agent guidance — referenced by status JSON, SKILL.md, CLI output.
"""

from __future__ import annotations

VERSION = "2.1"


MUST_KNOW = [
    "Multilogin X exposes Chrome DevTools Protocol (CDP). You control the browser with explicit CDP methods only — no indexed `ui click` shortcuts.",
    "The AI controller is your host AgentSkills runtime (Cursor/Claude/etc.), not Browser Use cloud and not a Browser Use API key flow.",
    "Start: `{cli} connect --account <name>` (starts MLX; does NOT save a session file unless `--persist-session`).",
    "On each new page: `{cli} cdp survey --account <name>` FIRST — scrolls the page, saves PNG snapshots per viewport, analyzes text; open every `screenshot_path` with vision before acting.",
    "Verify visually: `{cli} cdp snapshot --account <name> [path.png]` after important actions (CDP Page.captureScreenshot).",
    "Every CDP command needs `--account <name>`: `{cli} cdp survey`, `cdp session`, `cdp send --account <name> <Method> --params '<json>'`.",
    "MLX launcher is source of truth for whether a profile is running — no auto-load of last account.",
    "Examples: `{cli} cdp catalog`. Every navigation, click, type, and read must be a CDP send you choose.",
    "Verify with CDP (e.g. Runtime.evaluate on document text) before claiming login/post success.",
    "MLX profile = proxy + fingerprint + cookies. No browser-use CLI or API key.",
    "End: `{cli} disconnect --account <name>`. Never `multilogin stop-all` mid-task.",
    "Scrape without browser: `{cli} scrape \"<url>\" --json`.",
]


POLICY = """
Read `{cli} status` first.
Install skill: `{cli} agent install --host all --force`

MLX + raw CDP (no shortcuts):
  Start:  {cli} connect --account <name>
  Orient: {cli} cdp session
  Survey: {cli} cdp survey --account <name>   # read segments + PNG screenshot_path files
  Loop:   {cli} cdp send <Method> --params '{{...}}'  (only after survey + snapshots)
  Proof:  {cli} cdp snapshot --account <name> + Runtime.evaluate — vision + JSON before claiming success
  End:    {cli} disconnect --account <name>
""".strip()


def automation_guide() -> dict:
    return {
        "version": VERSION,
        "stack": {
            "browser": "multilogin",
            "proxy": "mlx profile (configured in Multilogin app)",
            "automation": "cdp_raw",
            "captcha": "optional",
        },
        "use_cases": {
            "accounts": {
                "connect": "{cli} connect --account <name>",
                "cdp": "{cli} cdp send <Domain.method> --params '<json>'",
                "disconnect": "{cli} disconnect --account <name>",
            },
            "scrape": {
                "fetch": '{cli} scrape "<url>" --json',
            },
        },
        "must_know": MUST_KNOW,
        "ask_user_before": [
            "Which MLX account to use",
            "Site username / password if login needed",
        ],
        "never": [
            "nextbrowser ui / state / click / type / close (legacy indexed shortcuts — blocked)",
            "Any external browser-automation product or extra LLM API key — the host agent IS the controller",
            "Claiming success without cdp survey + CDP proof",
            "multilogin stop-all mid-task",
        ],
    }


def command_recipes() -> dict:
    return {
        "policy": POLICY,
        "agent_must_know": MUST_KNOW,
        "automation": automation_guide(),
        "connect": "{cli} connect --account <name>",
        "cdp_survey": "{cli} cdp survey --account <name>",
        "cdp_snapshot": "{cli} cdp snapshot --account <name>",
        "cdp_session": "{cli} cdp session --account <name>",
        "cdp_send": "{cli} cdp send <Domain.method> --params '<json>'",
        "cdp_catalog": "{cli} cdp catalog",
        "disconnect": "{cli} disconnect --account <name>",
        "cdp_navigate": "{cli} cdp navigate --account <name> <url>",
        "login": "{cli} login <name> --url <url>  # deterministic: fill creds + submit + verify",
        "set_credentials": "{cli} account set-credentials <name> --username U --password P",
        "scrape": '{cli} scrape "<url>" --json',
        "mlx_doctor": "{cli} multilogin doctor",
        "agent_install": "{cli} agent install --host all --force",
        "agent_doctor": "{cli} agent doctor",
    }


def render(cli_prefix: str) -> dict:
    guide = automation_guide()
    recipes = command_recipes()

    def sub(obj):
        if isinstance(obj, str):
            return obj.replace("{cli}", cli_prefix)
        if isinstance(obj, list):
            return [sub(x) for x in obj]
        if isinstance(obj, dict):
            return {k: sub(v) for k, v in obj.items()}
        return obj

    return {
        "version": VERSION,
        "spec": "Nextbrowser Harness MVP v1.3 — account automation (MLX + raw CDP) & tiered scraping",
        "agent_must_know": sub(MUST_KNOW),
        "commands": sub(recipes),
        "automation": sub(guide),
    }
