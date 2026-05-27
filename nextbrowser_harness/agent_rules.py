"""
Single source of truth for agent guidance — referenced by status JSON, SKILL.md, CLI output.
"""

from __future__ import annotations

VERSION = "2.1"


MUST_KNOW = [
    "Multilogin X exposes Chrome DevTools Protocol (CDP). You control the browser with explicit CDP methods only — no indexed `ui click` shortcuts.",
    "Start: `{cli} connect --account <name>` → `{cli} cdp session` (CDP URL + active page).",
    "Act/observe: `{cli} cdp send <Domain.method> --params '<json>'` — e.g. Page.navigate, DOM.getDocument, Input.dispatchMouseEvent, Runtime.evaluate.",
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
  Loop:   {cli} cdp send <Method> --params '{{...}}'
  Proof:  cdp send Runtime.evaluate / DOM.* — confirm in JSON result before claiming success
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
            "Using ui click/type indices instead of CDP when automating accounts",
            "browser-use CLI as a required dependency",
            "Claiming success without CDP proof in command output",
            "multilogin stop-all mid-task",
        ],
    }


def command_recipes() -> dict:
    return {
        "policy": POLICY,
        "agent_must_know": MUST_KNOW,
        "automation": automation_guide(),
        "connect": "{cli} connect --account <name>",
        "cdp_session": "{cli} cdp session",
        "cdp_send": "{cli} cdp send <Domain.method> --params '<json>'",
        "cdp_catalog": "{cli} cdp catalog",
        "disconnect": "{cli} disconnect --account <name>",
        "login": "{cli} login <account> --url <url>",
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
        "spec": "Nextbrowser Harness MVP — MLX raw CDP",
        "agent_must_know": sub(MUST_KNOW),
        "commands": sub(recipes),
        "automation": sub(guide),
    }
