"""Start/stop Multilogin X profiles and expose their CDP URL for raw CDP control."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from nextbrowser_harness.accounts.registry import AccountRegistry
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.client import MultiloginXClient, MultiloginXError
from nextbrowser_harness.integrations.multilogin.platform_hints import ensure_mlx_launcher_running

SESSION_PATH = Path.home() / ".nextbrowser" / "mlx_cdp_session.json"


def _session_path() -> Path:
    p = Path(os.getenv("NEXTBROWSER_MLX_SESSION", str(SESSION_PATH)))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def save_session(data: dict[str, Any]) -> Path:
    path = _session_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_session() -> dict[str, Any] | None:
    path = _session_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def connect_account(
    config: HarnessConfig,
    account_id: str,
    *,
    headless: bool = False,
    persist_session: bool = False,
) -> dict[str, Any]:
    """Start the MLX profile for an account and return its CDP URL.

    Does not attach Playwright — the host agent drives the browser with raw CDP
    (`nextbrowser cdp send/survey/snapshot`). No session file is written unless
    ``persist_session`` is set.
    """
    account = AccountRegistry(config).require_for_tier3(account_id)
    layer_cfg = dict(config.multilogin or {})
    layer_cfg.setdefault("profiles", {})[account_id] = account.mlx_profile_id
    if account.mlx_folder_id:
        layer_cfg.setdefault("folder_id", account.mlx_folder_id)

    from nextbrowser_harness.integrations.multilogin.browser import MultiloginBrowserLayer

    layer = MultiloginBrowserLayer.from_config(config)
    folder_id, mlx_profile_id = layer.resolve_profile_id(account_id)

    launcher = ensure_mlx_launcher_running()
    if not launcher.get("launcher_reachable_after"):
        raise MultiloginXError(
            "Multilogin launcher not reachable. Run: nextbrowser multilogin doctor"
        )

    client = MultiloginXClient()
    started = client.start_profile(
        folder_id,
        mlx_profile_id,
        automation_type="playwright",
        headless=headless,
    )
    cdp = started.cdp_url
    if not cdp:
        raise MultiloginXError(f"No CDP port from MLX for profile {mlx_profile_id}")

    if persist_session:
        save_session(
            {
                "account_id": account_id,
                "mlx_profile_id": mlx_profile_id,
                "folder_id": folder_id,
                "cdp_url": cdp,
                "engine": "mlx+cdp",
                "keep_alive": True,
            }
        )
        from nextbrowser_harness.integrations.multilogin.session import mark_keep_alive

        mark_keep_alive(
            account_id,
            mlx_profile_id=mlx_profile_id,
            folder_id=folder_id,
            cdp_url=cdp,
            reason="mlx",
        )
    AccountRegistry(config).touch_run(account_id)

    return {
        "success": True,
        "account_id": account_id,
        "mlx_profile_id": mlx_profile_id,
        "cdp_url": cdp,
        "connection": "cdp",
        "keep_alive": True,
        "engine": "mlx+cdp",
        "session_persisted": persist_session,
        "next_commands": [
            f"nextbrowser cdp survey --account {account_id}",
            f"nextbrowser cdp session --account {account_id}",
            f'nextbrowser cdp send --account {account_id} Page.navigate --params \'{{"url":"https://..."}}\'',
            f"nextbrowser disconnect --account {account_id}",
        ],
        "agent_must_know": [
            f"MLX profile '{account_id}' on CDP {cdp}. Pass --account {account_id} on every cdp command.",
            "No session file unless you used connect --persist-session.",
            f"Control via `nextbrowser cdp send --account {account_id} <Domain.method>`.",
            f"End: nextbrowser disconnect --account {account_id}",
        ],
        "agent_prompt": (
            f"MLX CDP ready for account '{account_id}' ({cdp}). "
            f"Always: --account {account_id} on cdp send/session. "
            f"Done: disconnect --account {account_id}"
        ),
    }


def disconnect_account(
    config: HarnessConfig,
    account_id: str,
) -> dict[str, Any]:
    """Stop the MLX profile and clear keep-alive (call when the task is fully done)."""
    from nextbrowser_harness.integrations.multilogin.session import clear_keep_alive

    acc = AccountRegistry(config).get(account_id)
    mlx_id = acc.mlx_profile_id if acc else ""
    if mlx_id:
        try:
            MultiloginXClient().stop_profile(mlx_id)
        except Exception:
            pass
    clear_keep_alive(account_id or None)
    sess = load_session() or {}
    if sess.get("account_id") == account_id:
        path = _session_path()
        if path.is_file():
            path.unlink(missing_ok=True)
    return {"success": True, "account_id": account_id, "stopped_mlx_profile": mlx_id}
