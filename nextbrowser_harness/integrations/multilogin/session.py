"""Track MLX profiles that must stay running (login flows, browser-use CDP)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

KEEP_ALIVE_PATH = Path.home() / ".nextbrowser" / "mlx_keep_alive.json"


def _path() -> Path:
    p = Path(os.getenv("NEXTBROWSER_MLX_KEEP_ALIVE", str(KEEP_ALIVE_PATH)))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load() -> dict[str, dict[str, Any]]:
    path = _path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: dict[str, dict[str, Any]]) -> None:
    _path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def mark_keep_alive(
    account_key: str,
    *,
    mlx_profile_id: str,
    folder_id: str = "",
    cdp_url: str | None = None,
    reason: str = "browser-use",
) -> None:
    data = _load()
    data[account_key] = {
        "mlx_profile_id": mlx_profile_id,
        "folder_id": folder_id,
        "cdp_url": cdp_url,
        "reason": reason,
        "keep_alive": True,
    }
    _save(data)


def clear_keep_alive(account_key: str | None = None) -> None:
    data = _load()
    if account_key is None:
        data = {}
    else:
        data.pop(account_key, None)
    _save(data)


def should_keep_alive(account_key: str, mlx_profile_id: str | None = None) -> bool:
    entry = _load().get(account_key)
    if not entry or not entry.get("keep_alive"):
        return False
    if mlx_profile_id and entry.get("mlx_profile_id") != mlx_profile_id:
        return False
    return True


def list_keep_alive() -> dict[str, dict[str, Any]]:
    return _load()
