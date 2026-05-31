"""
Early CLI dispatch for MLX + raw CDP control.

Handles ``connect`` / ``disconnect`` / ``login`` / ``cdp`` before argparse, and
rejects legacy ``ui`` / ``state`` / ``click`` aliases with a CDP-only message.
"""

from __future__ import annotations

import argparse
import json
import sys

from nextbrowser_harness.accounts.registry import Tier3AccountError
from nextbrowser_harness.cdp_only import legacy_command_rejected
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.mlx_cdp.bridge import connect_account, disconnect_account

# Bare verbs that used to map to the legacy indexed UI — now blocked so agents use raw CDP.
LEGACY_UI_VERBS = frozenset(
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
        "ui",
        "mcp",
    }
)


def is_legacy_ui_verb(word: str) -> bool:
    return word in LEGACY_UI_VERBS


def cmd_connect(config: HarnessConfig, argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="nextbrowser connect")
    p.add_argument("--account", required=True)
    p.add_argument("--headless", action="store_true")
    p.add_argument(
        "--persist-session",
        action="store_true",
        help="Write ~/.nextbrowser session file (off by default)",
    )
    ns = p.parse_args(argv)
    try:
        out = connect_account(
            config,
            ns.account,
            headless=ns.headless,
            persist_session=ns.persist_session,
        )
    except Tier3AccountError as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        return 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        return 1
    print(json.dumps(out, indent=2))
    acct = ns.account
    print(
        f"\nCDP control for '{acct}':\n"
        f"  nextbrowser cdp send --account {acct} Page.navigate --params '{{\"url\":\"https://...\"}}'\n"
        f"  nextbrowser cdp survey --account {acct}   # PNG per viewport — open with vision\n"
        f"  nextbrowser cdp snapshot --account {acct}\n"
        f"  nextbrowser cdp send --account {acct} <Domain.method> --params '<json>'\n"
        f"  nextbrowser disconnect --account {acct}\n",
        file=sys.stderr,
    )
    return 0


def cmd_login(config: HarnessConfig, argv: list[str]) -> int:
    """Auto-login over CDP: connect, fill credentials, submit, verify (survey if no creds)."""
    p = argparse.ArgumentParser(prog="nextbrowser login")
    p.add_argument("account_id")
    p.add_argument("--url", required=True)
    p.add_argument("--username", default=None)
    p.add_argument("--password", default=None)
    p.add_argument("--site", default="")
    p.add_argument("--no-create", action="store_true")
    p.add_argument("--close", action="store_true", help="Disconnect MLX when done")
    ns = p.parse_args(argv)
    from nextbrowser_harness.workflows.login import login as login_workflow

    res = login_workflow(
        config,
        ns.account_id,
        url=ns.url,
        username=ns.username,
        password=ns.password,
        site=ns.site,
        create_if_missing=not ns.no_create,
        keep_open=not ns.close,
    )
    print(json.dumps(res.to_dict(), indent=2))
    return 0 if res.success else 1


def cmd_disconnect(config: HarnessConfig, argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="nextbrowser disconnect")
    p.add_argument("--account", required=True)
    ns = p.parse_args(argv)
    print(json.dumps(disconnect_account(config, ns.account), indent=2))
    return 0


def _reject_legacy(verb: str, argv: list[str]) -> int:
    account = None
    for i, a in enumerate(argv):
        if a == "--account" and i + 1 < len(argv):
            account = argv[i + 1]
            break
    print(json.dumps(legacy_command_rejected(verb, account=account), indent=2))
    return 1


def try_dispatch_cdp(config: HarnessConfig, argv: list[str]) -> int | None:
    """Intercept connect/disconnect/login/cdp and reject legacy verbs. Returns rc or None."""
    if not argv:
        return None
    head = argv[0]
    if head == "connect":
        return cmd_connect(config, argv[1:])
    if head == "disconnect":
        return cmd_disconnect(config, argv[1:])
    if head == "login":
        return cmd_login(config, argv[1:])
    if head == "cdp":
        from nextbrowser_harness.workflows import cdp_control

        return cdp_control.cli_main(config, argv[1:])
    if is_legacy_ui_verb(head):
        return _reject_legacy(head, argv[1:])
    return None
