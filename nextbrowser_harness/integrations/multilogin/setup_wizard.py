"""Interactive Multilogin X setup — email in .env, password never persisted."""

from __future__ import annotations

import getpass
import json
import os
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.client import MultiloginXClient, MultiloginXError
from nextbrowser_harness.integrations.multilogin.platform_hints import (
    fix_linux_mlx_launcher_script,
    mlx_install_check,
    try_start_mlx_desktop,
)
from nextbrowser_harness.platform_paths import is_linux
from nextbrowser_harness.onboarding import _apply_multilogin_env


MLX_DOWNLOAD_URL = "https://multilogin.com"


@dataclass
class SetupWizardOptions:
    env_file: Path
    profile_key: str = "default"
    skip_signin: bool = False
    non_interactive: bool = False
    open_download: bool = True


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_env_path(env_file: str | Path | None = None) -> Path:
    if env_file:
        p = Path(env_file).expanduser()
        return p if p.is_absolute() else _repo_root() / p
    local = _repo_root() / ".env"
    return local if local.exists() else Path.cwd() / ".env"


def update_dotenv(path: Path, updates: dict[str, str]) -> None:
    """Merge key=value pairs into .env without touching unrelated lines."""
    lines: list[str] = []
    seen: set[str] = set()
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in updates:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        out.append(line)
    for key, val in updates.items():
        if key not in seen:
            out.append(f"{key}={val}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def load_dotenv_into_os(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{text}{suffix}: ").strip()
    return val or default


def _select_from_list(items: list[dict[str, Any]], *, prompt: str, non_interactive: bool) -> dict[str, Any]:
    if not items:
        raise MultiloginXError("No items returned from Multilogin API.")
    for i, item in enumerate(items):
        uid = item.get("id") or item.get("uuid") or ""
        name = item.get("name") or item.get("profile_name") or "(no name)"
        print(f"  [{i}] {name}  ({uid})")
    if non_interactive and len(items) == 1:
        return items[0]
    idx_raw = input(f"{prompt} [0-{len(items) - 1}]: ").strip()
    try:
        idx = int(idx_raw)
    except ValueError as e:
        raise MultiloginXError(f"Invalid selection: {idx_raw}") from e
    if idx < 0 or idx >= len(items):
        raise MultiloginXError(f"Selection out of range: {idx}")
    return items[idx]


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("uuid") or "")


def _has_saved_token(client: MultiloginXClient) -> bool:
    if os.getenv("MULTILOGIN_AUTOMATION_TOKEN") or os.getenv("MULTILOGIN_TOKEN"):
        return True
    if not client.token_path.exists():
        return False
    import yaml

    data = yaml.safe_load(client.token_path.read_text(encoding="utf-8")) or {}
    return bool(data.get("automation_token") or data.get("token"))


def run_setup_wizard(
    *,
    cfg: HarnessConfig | None = None,
    options: SetupWizardOptions | None = None,
    client: MultiloginXClient | None = None,
) -> dict[str, Any]:
    """
    Guided MLX setup: desktop check, secure signin, folder/profile picker, .env + init.
    Password is never written to disk.
    """
    opts = options or SetupWizardOptions(env_file=resolve_env_path())
    env_path = Path(opts.env_file).expanduser()
    client = client or MultiloginXClient()

    print("\n=== Multilogin X setup wizard ===\n")

    if is_linux():
        fix = fix_linux_mlx_launcher_script(apply=True)
        if fix.get("applied"):
            print(f"Linux: {fix.get('message')}")

    install = mlx_install_check()
    if not install.get("installed"):
        print(f"Multilogin X desktop app not found.")
        print(f"  Download: {MLX_DOWNLOAD_URL}")
        for p in install.get("checked_paths", []):
            print(f"  Checked: {p}")
        if opts.open_download and not opts.non_interactive:
            open_dl = input("Open download page in browser? [Y/n]: ").strip().lower()
            if open_dl != "n":
                webbrowser.open(MLX_DOWNLOAD_URL)
        if not opts.non_interactive:
            input("Install MLX, then press Enter to continue...")
        install = mlx_install_check()
        if not install.get("installed"):
            print("Warning: MLX app still not detected — launcher may be unreachable until installed.")

    print("Starting Multilogin X desktop app (if needed)...")
    try_start_mlx_desktop()

    load_dotenv_into_os(env_path)

    email = os.getenv("MULTILOGIN_EMAIL", "").strip()
    if not opts.skip_signin and not _has_saved_token(client):
        if not email:
            email = _prompt("Multilogin X email")
        password = getpass.getpass("Multilogin X password (not saved): ")
        if not email or not password:
            raise MultiloginXError("Email and password are required for signin.")
        try:
            client.signin(email, password)
            client.fetch_automation_token()
        except MultiloginXError as e:
            print(str(e), file=sys.stderr)
            print("\nUse your Multilogin X app login at https://app.multilogin.com", file=sys.stderr)
            raise
        print(f"Tokens saved to {client.token_path} (password not stored).")
    elif opts.skip_signin:
        print("Skipping sign-in (--skip-signin). Using saved token or MULTILOGIN_AUTOMATION_TOKEN.")
    else:
        print("Using existing automation token.")

    folder_id = os.getenv("MULTILOGIN_FOLDER_ID", "").strip()
    if not folder_id:
        folders = client.list_folders()
        print("\nWorkspace folders:")
        picked = _select_from_list(folders, prompt="Folder", non_interactive=opts.non_interactive)
        folder_id = _item_id(picked)
    if not folder_id:
        raise MultiloginXError("Folder id required.")

    profile_id = os.getenv("MULTILOGIN_PROFILE_ID", "").strip()
    if not profile_id:
        profiles = client.search_profiles(folder_id=folder_id, search_text="", limit=50)
        print("\nBrowser profiles:")
        picked = _select_from_list(profiles, prompt="Profile", non_interactive=opts.non_interactive)
        profile_id = _item_id(picked)
    if not profile_id:
        raise MultiloginXError("Profile id required.")

    profile_env_key = f"MULTILOGIN_PROFILE_{opts.profile_key.upper().replace('-', '_')}"
    env_updates = {
        "NEXTBROWSER_BROWSER": "multilogin",
        "NEXTBROWSER_AUTOMATION": "playwright",
        "NEXTBROWSER_PROXY": "none",
        "MULTILOGIN_FOLDER_ID": folder_id,
        "MULTILOGIN_PROFILE_ID": profile_id,
        profile_env_key: profile_id,
    }
    if email:
        env_updates["MULTILOGIN_EMAIL"] = email
    elif os.getenv("MULTILOGIN_EMAIL"):
        env_updates["MULTILOGIN_EMAIL"] = os.getenv("MULTILOGIN_EMAIL", "")

    update_dotenv(env_path, env_updates)
    load_dotenv_into_os(env_path)
    print(f"\nWrote {env_path}")

    cfg = cfg or HarnessConfig.load()
    cfg.browser = "multilogin"  # type: ignore[assignment]
    cfg.proxy = "none"  # type: ignore[assignment]
    cfg.multilogin = {
        "folder_id": folder_id,
        "default_profile_id": profile_id,
        "profiles": {opts.profile_key: profile_id},
    }
    _apply_multilogin_env(cfg)
    cfg.save()

    from nextbrowser_harness.integrations.multilogin.doctor import mlx_doctor_report

    report = mlx_doctor_report(client)
    print("\n--- Doctor ---")
    print(json.dumps(report, indent=2))
    if report.get("next_steps"):
        print("\nNext steps:")
        for i, step in enumerate(report["next_steps"], 1):
            print(f"  {i}. {step}")

    result = {
        "env_file": str(env_path),
        "folder_id": folder_id,
        "profile_id": profile_id,
        "profile_key": opts.profile_key,
        "doctor_ok": bool(report.get("ok")),
        "doctor": report,
    }
    print("\nTest:")
    print(
        f'  nextbrowser exec "https://example.com" --browser multilogin '
        f'--profile {opts.profile_key} --tier 3'
    )
    return result
