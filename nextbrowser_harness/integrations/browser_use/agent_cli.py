"""
Native MLX + Playwright passthrough for any AgentSkills host agent.

Same UX as browser-use (state / click / input) — no browser-use binary or API key.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from nextbrowser_harness.accounts.registry import Tier3AccountError
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.browser_use.bridge import connect_account, disconnect_account
from nextbrowser_harness.workflows import ui as ui_workflow

BROWSER_USE_VERBS = frozenset(
    {
        "open",
        "back",
        "scroll",
        "state",
        "screenshot",
        "click",
        "type",
        "input",
        "keys",
        "select",
        "upload",
        "hover",
        "dblclick",
        "rightclick",
        "eval",
        "get",
        "wait",
        "cookies",
        "close",
        "tab",
        "sessions",
    }
)


def is_browser_use_verb(word: str) -> bool:
    return word in BROWSER_USE_VERBS


def cmd_connect(config: HarnessConfig, argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="nextbrowser connect")
    p.add_argument("--account", required=True)
    p.add_argument("--headless", action="store_true")
    ns = p.parse_args(argv)
    try:
        out = connect_account(config, ns.account, headless=ns.headless)
    except Tier3AccountError as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        return 1
    print(json.dumps(out, indent=2))
    print(
        "\nMLX CDP is open. Host agent controls it with raw CDP only:\n"
        "  nextbrowser cdp session\n"
        '  nextbrowser cdp send Page.navigate --params \'{"url":"https://..."}\'\n'
        "  nextbrowser cdp send DOM.getDocument --params '{\"depth\":-1,\"pierce\":true}'\n"
        "  nextbrowser cdp catalog   # method examples\n"
        "No indexed shortcuts. Proxy = MLX profile only.",
        file=sys.stderr,
    )
    return 0


def cmd_disconnect(config: HarnessConfig, argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="nextbrowser disconnect")
    p.add_argument("--account", required=True)
    ns = p.parse_args(argv)
    print(json.dumps(disconnect_account(config, ns.account), indent=2))
    return 0


def cmd_passthrough(config: HarnessConfig, argv: list[str]) -> int:
    if not argv:
        return 1
    verb = argv[0]
    if verb == "close":
        out = ui_workflow.close(config)
        print(json.dumps(out, indent=2))
        return 0
    args = argv[1:]
    if verb in ("type", "input") and args:
        res = ui_workflow.run(config, "input", args=[args[0], args[1] if len(args) > 1 else ""])
    elif verb == "click" and args:
        res = ui_workflow.run(config, "click", args=[args[0]])
    elif verb == "open" and args:
        res = ui_workflow.run(config, "open", args=[args[0]])
    elif verb == "scroll":
        res = ui_workflow.run(config, "scroll", args=args or ["down"])
    else:
        res = ui_workflow.run(config, verb, args=args)
    if res.stdout:
        print(res.stdout)
    if res.error:
        print(res.error, file=sys.stderr)
    return 0 if res.success else 1


def try_dispatch_native_browser_use(config: HarnessConfig, argv: list[str]) -> int | None:
    if not argv:
        return None
    head = argv[0]
    if head == "connect":
        return cmd_connect(config, argv[1:])
    if head == "disconnect":
        return cmd_disconnect(config, argv[1:])
    if head == "cdp":
        from nextbrowser_harness.workflows import cdp_control

        return cdp_control.cli_main(config, argv[1:])
    if head == "mcp":
        print(
            json.dumps(
                {
                    "error": "MCP mode removed — use MLX + Playwright only.",
                    "use": "nextbrowser connect --account <name> then nextbrowser ui state",
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    if is_browser_use_verb(head):
        return cmd_passthrough(config, argv)
    return None
