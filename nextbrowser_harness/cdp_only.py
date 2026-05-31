"""Enforce raw CDP — block the legacy ui/indexed-click shortcuts."""

from __future__ import annotations

from typing import Any

FORBIDDEN_PREFIXES = (
    "ui ",
    "ui\t",
)


def cdp_workflow(account: str, *, url: str | None = None) -> list[str]:
    lines = [
        f"nextbrowser disconnect --account {account}",
        f"nextbrowser connect --account {account}",
    ]
    if url:
        esc = url.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(
            f'nextbrowser cdp send --account {account} Page.navigate '
            f'--params \'{{"url":"{esc}"}}\''
        )
    lines.extend(
        [
            f"nextbrowser cdp survey --account {account}",
            f"nextbrowser cdp send --account {account} <Domain.method> --params '<json>'",
            f"nextbrowser disconnect --account {account}",
        ]
    )
    return lines


def legacy_command_rejected(what: str, *, account: str | None = None) -> dict[str, Any]:
    acct = account or "<name>"
    return {
        "success": False,
        "error": f"'{what}' is disabled. Use Chrome DevTools Protocol (CDP) only.",
        "never_use": [
            "nextbrowser ui state|click|type|close",
            "nextbrowser state|click|type|close (bare aliases)",
        ],
        "use_instead": cdp_workflow(acct),
        "agent_must_know": (
            "MLX account automation = connect + cdp send + cdp survey + disconnect. "
            "Always pass --account on every command."
        ),
    }
