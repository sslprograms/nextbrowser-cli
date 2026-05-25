"""Multilogin X health check — structured report for humans and agents."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
import yaml

from nextbrowser_harness.integrations.multilogin.client import (
    LAUNCHER_BASE,
    MultiloginXClient,
)
from nextbrowser_harness.integrations.multilogin.platform_hints import (
    ensure_display_linux,
    mlx_install_check,
    mlx_launcher_unreachable_message,
    mlx_setup_script_hint,
    mlx_setup_wizard_command,
    mlx_start_desktop_hint,
    xvfb_available,
)
from nextbrowser_harness.platform_paths import system_name


def _token_file_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "keys": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keys = list(data.keys())
    return {
        "exists": True,
        "path": str(path),
        "keys": keys,
        "has_automation_token": bool(data.get("automation_token")),
        "has_token": bool(data.get("token")),
        "has_refresh": bool(data.get("refresh_token")),
        "email_saved": bool(data.get("email")),
    }


def mlx_doctor_report(client: MultiloginXClient | None = None) -> dict[str, Any]:
    client = client or MultiloginXClient()
    launcher_url = os.getenv("MULTILOGIN_LAUNCHER_URL", LAUNCHER_BASE)
    folder_id = os.getenv("MULTILOGIN_FOLDER_ID", "")
    profile_id = os.getenv("MULTILOGIN_PROFILE_ID", "")
    profile_reddit = os.getenv("MULTILOGIN_PROFILE_REDDIT_DEFAULT", "")

    install = mlx_install_check()
    display = ensure_display_linux()

    report: dict[str, Any] = {
        "os": system_name(),
        "launcher_url": launcher_url,
        "launcher_reachable": False,
        "launcher_status": None,
        "launcher_error": None,
        "mlx_app_installed": install.get("installed"),
        "mlx_checked_paths": install.get("checked_paths", []),
        "display_ok": display.get("display_ok"),
        "xvfb_available": xvfb_available() if display.get("needed") else None,
        "display_hint": display.get("install_hint") or None,
        "token_file": _token_file_status(client.token_path),
        "env": {
            "MULTILOGIN_EMAIL": bool(os.getenv("MULTILOGIN_EMAIL")),
            "MULTILOGIN_PASSWORD": bool(os.getenv("MULTILOGIN_PASSWORD")),
            "MULTILOGIN_AUTOMATION_TOKEN": bool(os.getenv("MULTILOGIN_AUTOMATION_TOKEN")),
            "MULTILOGIN_FOLDER_ID": folder_id,
            "MULTILOGIN_PROFILE_ID": profile_id,
            "MULTILOGIN_PROFILE_REDDIT_DEFAULT": profile_reddit,
            "NEXTBROWSER_BROWSER": os.getenv("NEXTBROWSER_BROWSER", ""),
        },
        "api_token_ok": False,
        "api_error": None,
        "profile_key_reddit_default": bool(profile_reddit or profile_id),
        "ok": False,
        "next_steps": [],
        "setup_wizard_command": mlx_setup_wizard_command(),
        "setup_script": mlx_setup_script_hint(),
        "start_desktop_hint": mlx_start_desktop_hint(),
    }

    try:
        r = requests.get(launcher_url, timeout=5, verify=False)
        report["launcher_reachable"] = r.status_code < 500
        report["launcher_status"] = r.status_code
    except Exception as e:
        report["launcher_error"] = str(e)

    try:
        client.ensure_token()
        report["api_token_ok"] = True
    except Exception as e:
        report["api_error"] = str(e)

    steps: list[str] = []
    if not report["mlx_app_installed"]:
        steps.append(
            f"Install Multilogin X desktop app from {install.get('download_url', 'https://multilogin.com')}, "
            f"then run: {mlx_setup_wizard_command()}"
        )
    if display.get("needed") and not display.get("display_ok"):
        steps.append(display.get("install_hint") or "Install xvfb for headless Linux MLX")
    if not report["launcher_reachable"]:
        steps.append(mlx_launcher_unreachable_message())
    if not report["api_token_ok"]:
        steps.append(
            f"Auth: run `{mlx_setup_wizard_command()}` or "
            "`nextbrowser multilogin signin` then `nextbrowser multilogin automation-token`. "
            "Do NOT edit ~/.nextbrowser/multilogin_tokens.yaml by hand."
        )
    elif not report["token_file"].get("has_automation_token"):
        steps.append("Run: nextbrowser multilogin automation-token")
    if not folder_id:
        steps.append("Run setup-wizard or: nextbrowser multilogin folders — set MULTILOGIN_FOLDER_ID")
    if not profile_id:
        steps.append(
            "Run setup-wizard or: nextbrowser multilogin profiles --folder-id $MULTILOGIN_FOLDER_ID — "
            "set MULTILOGIN_PROFILE_ID"
        )
    if not profile_reddit and profile_id:
        steps.append(
            "For --profile reddit_default also set: "
            f"MULTILOGIN_PROFILE_REDDIT_DEFAULT={profile_id or '<uuid>'}"
        )
    if report["env"].get("NEXTBROWSER_BROWSER") != "multilogin":
        steps.append("Set NEXTBROWSER_BROWSER=multilogin and run: nextbrowser init --env")

    report["next_steps"] = steps
    report["ok"] = (
        report["launcher_reachable"]
        and report["api_token_ok"]
        and bool(folder_id)
        and bool(profile_id)
        and report["env"].get("NEXTBROWSER_BROWSER") == "multilogin"
        and (report["display_ok"] is not False)
    )
    return report


def mlx_print_env_snippet() -> str:
    """Lines to append to .env (no secrets)."""
    folder = os.getenv("MULTILOGIN_FOLDER_ID", "")
    profile = os.getenv("MULTILOGIN_PROFILE_ID", "")
    lines = [
        "NEXTBROWSER_BROWSER=multilogin",
        "NEXTBROWSER_AUTOMATION=playwright",
        "NEXTBROWSER_PROXY=none",
    ]
    if folder:
        lines.append(f"MULTILOGIN_FOLDER_ID={folder}")
    if profile:
        lines.append(f"MULTILOGIN_PROFILE_ID={profile}")
        lines.append(f"MULTILOGIN_PROFILE_REDDIT_DEFAULT={profile}")
    email = os.getenv("MULTILOGIN_EMAIL", "")
    if email:
        lines.append(f"MULTILOGIN_EMAIL={email}")
    return "\n".join(lines)
