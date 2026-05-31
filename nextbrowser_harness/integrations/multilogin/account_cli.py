"""Explicit MLX account selection — no implicit session file."""

from __future__ import annotations

from typing import Any


class AccountRequiredError(RuntimeError):
    pass


def parse_account_flags(argv: list[str]) -> tuple[str | None, bool, bool, list[str]]:
    """
    Parse --account, --use-saved-session, --persist-session from argv.

    Returns (account, use_saved_session, persist_session, remaining_argv).
    """
    account: str | None = None
    use_saved = False
    persist = False
    out: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--account" and i + 1 < len(argv):
            account = argv[i + 1]
            i += 2
            continue
        if a == "--use-saved-session":
            use_saved = True
            i += 1
            continue
        if a == "--persist-session":
            persist = True
            i += 1
            continue
        out.append(a)
        i += 1
    return account, use_saved, persist, out


def resolve_account_id(
    account: str | None,
    *,
    use_saved_session: bool = False,
) -> str:
    """Require --account unless user explicitly opted into saved session file."""
    if account and str(account).strip():
        return str(account).strip()
    if use_saved_session:
        from nextbrowser_harness.integrations.mlx_cdp.bridge import load_session

        sess = load_session() or {}
        saved = (sess.get("account_id") or "").strip()
        if saved:
            return saved
        raise AccountRequiredError(
            "--use-saved-session set but no session file. "
            "Run: nextbrowser connect --account <name> --persist-session"
        )
    raise AccountRequiredError(
        "Pass --account <profile-name> on every MLX/CDP command. "
        "Session files are not loaded automatically."
    )


def resolve_running_cdp(
    config,
    account_id: str,
) -> tuple[str, str, str]:
    """CDP URL from MLX launcher for an already-running profile (no session file)."""
    from nextbrowser_harness.integrations.multilogin.browser import MultiloginBrowserLayer
    from nextbrowser_harness.integrations.multilogin.client import MultiloginXError

    layer = MultiloginBrowserLayer.from_config(config)
    folder_id, mlx_profile_id = layer.resolve_profile_id(account_id)
    running = layer.client.profile_running(mlx_profile_id, folder_id=folder_id)
    if not running or not running.cdp_url:
        raise MultiloginXError(
            f"MLX profile '{account_id}' is not running. "
            f"Start it: nextbrowser connect --account {account_id}"
        )
    return running.cdp_url, mlx_profile_id, folder_id
