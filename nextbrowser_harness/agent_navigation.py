"""Agent-facing navigation API — documents how hosts should drive the CLI (not raw Playwright)."""

from __future__ import annotations

AGENT_NAVIGATION_POLICY = """
Do NOT write standalone Playwright/Puppeteer/Selenium Python scripts unless the user explicitly asks.
Use the nextbrowser CLI from platform.cli (see: nextbrowser status).

Navigation (open browser + interact):
  nextbrowser exec "<url>" --action "goto" --action "click:SELECTOR" --action "eval:EXPRESSION"
  nextbrowser exec "<url>" --js "document.title"
  nextbrowser exec "<url>" --steps-file path/to/steps.json
  nextbrowser browse "<url>" --js "..."   # Reddit-oriented defaults

Read-only (no browser UI):
  nextbrowser scrape "<url>" --json
  nextbrowser tier lookup "<url>"

Persistent identity:
  nextbrowser account add <id>
  nextbrowser account run <id> "eval:document.title" --url "<url>"
""".strip()


def agent_command_recipes() -> dict:
    """Machine-readable hints returned in nextbrowser status for agents."""
    return {
        "policy": "Use nextbrowser CLI only; do not invent Playwright Python for navigation.",
        "read_page": "{cli} scrape \"<url>\" --json",
        "navigate": "{cli} exec \"<url>\" --steps-file examples/steps-reddit.json",
        "inject_js": "{cli} exec \"<url>\" --js \"document.title\"",
        "click_fill": "{cli} exec \"<url>\" --action \"fill:#id|value\" --action \"click:button.submit\"",
        "mlx": "{cli} multilogin doctor && {cli} exec \"<url>\" --browser multilogin --profile reddit_default",
        "mlx_setup_windows": ".\\scripts\\setup-multilogin.ps1",
        "mlx_setup_unix": "./scripts/setup-multilogin.sh",
        "mlx_setup": "{cli} multilogin setup",
        "mlx_forbidden": "Do not edit ~/.nextbrowser/multilogin_tokens.yaml by hand",
        "steps_format": {
            "url": "https://example.com",
            "actions": ["goto", "wait:2000", "title", "eval:document.title", "final_url"],
        },
        "action_prefixes": ["eval:", "jsfile:", "click:", "fill:", "wait:", "goto"],
    }
