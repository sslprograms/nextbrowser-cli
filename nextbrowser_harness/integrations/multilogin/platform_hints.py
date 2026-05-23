"""OS-specific Multilogin X desktop app paths and setup script hints."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from nextbrowser_harness.platform_paths import is_linux, is_macos, is_windows, repo_root


def mlx_setup_script_path() -> Path:
    root = repo_root()
    if is_windows():
        return root / "scripts" / "setup-multilogin.ps1"
    return root / "scripts" / "setup-multilogin.sh"


def mlx_setup_script_hint() -> str:
    p = mlx_setup_script_path()
    if is_windows():
        return f".\\scripts\\setup-multilogin.ps1"
    return "./scripts/setup-multilogin.sh"


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


def mlx_start_desktop_hint() -> str:
    if is_windows():
        return r"Start MLX: %LOCALAPPDATA%\Multilogin X App\MLXDesktopApp.exe"
    if is_macos():
        return 'Start MLX: open -a "Multilogin X App" (install from multilogin.com if missing)'
    if is_linux():
        return (
            "Start Multilogin X from your app menu, or set MULTILOGIN_APP_EXE to desktop.bin "
            "(often under /opt/mlx/ or /opt/mlxapp/)"
        )
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
        f"Then run guided setup: {mlx_setup_script_hint()} "
        f"or: nextbrowser multilogin setup"
    )
