"""OS-specific Multilogin X desktop app paths and setup script hints."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from nextbrowser_harness.platform_paths import is_linux, is_macos, is_windows, repo_root

MLX_DOWNLOAD_URL = "https://multilogin.com"


def mlx_setup_script_path() -> Path:
    root = repo_root()
    if is_windows():
        return root / "scripts" / "setup-multilogin.ps1"
    return root / "scripts" / "setup-multilogin.sh"


def mlx_setup_script_hint() -> str:
    if is_windows():
        return ".\\scripts\\setup-multilogin.ps1"
    return "./scripts/setup-multilogin.sh"


def mlx_setup_wizard_command() -> str:
    return "nextbrowser multilogin setup-wizard"


def mlx_desktop_paths() -> list[Path]:
    """Candidate MLX desktop binaries (newest paths first)."""
    custom = os.getenv("MULTILOGIN_APP_EXE", "").strip()
    if custom:
        return [Path(custom).expanduser()]
    paths: list[Path] = []
    if is_windows():
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            paths.append(Path(local) / "Multilogin X App" / "MLXDesktopApp.exe")
    elif is_macos():
        paths.extend(
            [
                Path("/Applications/Multilogin X App.app"),
                Path("/Applications/Multilogin X.app"),
                Path.home() / "Applications" / "Multilogin X App.app",
            ]
        )
    elif is_linux():
        paths.extend(
            [
                Path("/opt/mlx/desktop.bin"),
                Path("/opt/mlxapp/desktop.bin"),
                Path("/opt/mlx/agent.bin"),
            ]
        )
    return paths


def mlx_install_check() -> dict[str, Any]:
    """Verify MLX desktop binary exists; return paths checked."""
    checked = [str(p) for p in mlx_desktop_paths()]
    installed = any(Path(p).exists() for p in checked)
    return {
        "installed": installed,
        "checked_paths": checked,
        "download_url": MLX_DOWNLOAD_URL,
    }


def xvfb_available() -> bool:
    if not is_linux():
        return False
    return bool(shutil.which("xvfb-run")) and bool(shutil.which("Xvfb"))


def ensure_display_linux(*, install_hint_only: bool = True) -> dict[str, Any]:
    """
    Linux headless servers need Xvfb for MLX/UC desktop apps.
    install_hint_only: document apt install xvfb; do not run apt automatically.
    """
    if not is_linux():
        return {"needed": False, "xvfb_available": False, "display_ok": True}
    display = os.getenv("DISPLAY", "")
    has_display = bool(display.strip())
    xvfb_ok = xvfb_available()
    hint = ""
    if not has_display and not xvfb_ok and install_hint_only:
        hint = "Install Xvfb: sudo apt install xvfb  (or use xvfb-run -a for MLX launch)"
    return {
        "needed": not has_display,
        "display_ok": has_display or xvfb_ok,
        "xvfb_available": xvfb_ok,
        "display": display or None,
        "install_hint": hint,
    }


def _linux_mlx_launch_cmd(path: Path) -> list[str]:
    if xvfb_available():
        return ["xvfb-run", "-a", str(path)]
    return [str(path)]


def mlx_start_desktop_hint() -> str:
    if is_windows():
        return r"Start MLX: %LOCALAPPDATA%\Multilogin X App\MLXDesktopApp.exe"
    if is_macos():
        return 'Start MLX: open -a "Multilogin X App" (install from multilogin.com if missing)'
    if is_linux():
        disp = ensure_display_linux()
        base = (
            "Start Multilogin X from your app menu, or set MULTILOGIN_APP_EXE to desktop.bin "
            "(often under /opt/mlx/ or /opt/mlxapp/)"
        )
        if disp.get("needed") and not disp.get("display_ok"):
            return f"{base}. Headless Linux: {disp.get('install_hint', 'install xvfb')}"
        if disp.get("needed") and xvfb_available():
            return f"{base}. Headless: xvfb-run -a <desktop.bin>"
        return base
    return "Start the Multilogin X desktop app and ensure the launcher is on port 45001"


def try_start_mlx_desktop(*, wait_seconds: int = 8) -> bool:
    """Best-effort start MLX desktop; returns True if a start was attempted or app exists."""
    if os.getenv("MULTILOGIN_SKIP_APP_START", "").lower() in ("1", "true", "yes"):
        return False
    for path in mlx_desktop_paths():
        if not path.exists():
            continue
        try:
            if is_macos() and path.suffix == ".app":
                subprocess.Popen(["open", "-a", path.stem if path.name.endswith(".app") else str(path)])
                return True
            if is_linux() and path.is_file() and os.access(path, os.X_OK):
                cmd = _linux_mlx_launch_cmd(path)
                env = os.environ.copy()
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                return True
            if path.is_file() and os.access(path, os.X_OK):
                subprocess.Popen([str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            if is_windows() and path.suffix.lower() == ".exe":
                subprocess.Popen([str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        except OSError:
            continue
    if is_macos() and shutil.which("open"):
        try:
            subprocess.Popen(["open", "-a", "Multilogin X App"])
            return True
        except OSError:
            pass
    return False


def mlx_launcher_unreachable_message() -> str:
    return (
        f"{mlx_start_desktop_hint()}. "
        f"Then run: {mlx_setup_wizard_command()} "
        f"or guided script: {mlx_setup_script_hint()}"
    )
