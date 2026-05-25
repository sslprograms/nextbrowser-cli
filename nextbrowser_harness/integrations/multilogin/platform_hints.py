"""OS-specific Multilogin X desktop app paths and setup script hints."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from nextbrowser_harness.platform_paths import is_linux, is_macos, is_windows, repo_root

MLX_DOWNLOAD_URL = "https://multilogin.com"

# Debian .deb layout (common on Linux VPS)
LINUX_MLX_ROOT = Path("/opt/mlx")
LINUX_MLX_AGENT_BIN = LINUX_MLX_ROOT / "opt" / "mlx" / "agent.bin"
LINUX_MLX_LAUNCHER_SCRIPT = LINUX_MLX_ROOT / "usr" / "bin" / "mlx"
LINUX_MLX_WRONG_AGENT_PATH = LINUX_MLX_ROOT / "agent.bin"
# Wrong path string in broken .deb launcher scripts (always POSIX-style in shell scripts)
LINUX_MLX_DEB_AGENT_LEGACY_STR = "/opt/mlx/agent.bin"
LINUX_MLX_AGENT_BIN_STR = "/opt/mlx/opt/mlx/agent.bin"


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
    """Candidate MLX desktop binaries / launcher scripts (preferred first)."""
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
        if LINUX_MLX_LAUNCHER_SCRIPT.exists():
            paths.append(LINUX_MLX_LAUNCHER_SCRIPT)
        paths.extend(
            [
                LINUX_MLX_AGENT_BIN,
                Path("/opt/mlx/desktop.bin"),
                Path("/opt/mlxapp/desktop.bin"),
                LINUX_MLX_WRONG_AGENT_PATH,
            ]
        )
    return paths


def diagnose_linux_mlx_launcher() -> dict[str, Any]:
    """Detect broken /opt/mlx/usr/bin/mlx script pointing at wrong agent.bin path."""
    out: dict[str, Any] = {
        "applies": is_linux(),
        "launcher_script": str(LINUX_MLX_LAUNCHER_SCRIPT),
        "launcher_script_exists": LINUX_MLX_LAUNCHER_SCRIPT.is_file(),
        "agent_bin_correct": str(LINUX_MLX_AGENT_BIN),
        "agent_bin_exists": LINUX_MLX_AGENT_BIN.is_file(),
        "wrong_path_in_script": False,
        "fixable": False,
        "script_preview": None,
    }
    if not is_linux():
        return out
    if not LINUX_MLX_LAUNCHER_SCRIPT.is_file():
        return out
    try:
        text = LINUX_MLX_LAUNCHER_SCRIPT.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        out["read_error"] = str(e)
        return out
    out["script_preview"] = text[:500]
    wrong = LINUX_MLX_DEB_AGENT_LEGACY_STR
    correct = LINUX_MLX_AGENT_BIN_STR
    # Broken installs reference /opt/mlx/agent.bin but binary lives under /opt/mlx/opt/mlx/
    if wrong in text and correct not in text:
        out["wrong_path_in_script"] = True
    if LINUX_MLX_AGENT_BIN.is_file() and out["wrong_path_in_script"]:
        out["fixable"] = True
    return out


def fix_linux_mlx_launcher_script(*, apply: bool = True) -> dict[str, Any]:
    """
    Fix mlx launcher script when it points at /opt/mlx/agent.bin instead of
    /opt/mlx/opt/mlx/agent.bin (common .deb install bug).
    """
    diag = diagnose_linux_mlx_launcher()
    result = {**diag, "applied": False, "message": ""}
    if not diag.get("applies"):
        result["message"] = "Linux only"
        return result
    if not diag.get("launcher_script_exists"):
        result["message"] = f"Launcher script not found: {LINUX_MLX_LAUNCHER_SCRIPT}"
        return result
    if not diag.get("wrong_path_in_script"):
        result["message"] = "Launcher script path looks OK (or already fixed)"
        return result
    if not diag.get("fixable"):
        result["message"] = f"Cannot fix: missing {LINUX_MLX_AGENT_BIN}"
        return result
    wrong = LINUX_MLX_DEB_AGENT_LEGACY_STR
    correct = str(LINUX_MLX_AGENT_BIN) if LINUX_MLX_AGENT_BIN.exists() else LINUX_MLX_AGENT_BIN_STR
    text = LINUX_MLX_LAUNCHER_SCRIPT.read_text(encoding="utf-8", errors="replace")
    new_text = text.replace(wrong, correct)
    if new_text == text:
        # fallback: any /opt/mlx/agent.bin not under opt/mlx/opt/mlx
        new_text = re.sub(
            r"(/opt/mlx)/agent\.bin",
            r"\1/opt/mlx/agent.bin",
            text,
        )
    result["message"] = f"Replace {wrong} -> {correct}"
    if apply and new_text != text:
        LINUX_MLX_LAUNCHER_SCRIPT.write_text(new_text, encoding="utf-8")
        try:
            LINUX_MLX_LAUNCHER_SCRIPT.chmod(LINUX_MLX_LAUNCHER_SCRIPT.stat().st_mode | 0o111)
        except OSError:
            pass
        result["applied"] = True
        result["message"] = "Fixed launcher script path"
    elif not apply:
        result["message"] = "Dry run: would fix launcher script path"
    return result


def mlx_install_check() -> dict[str, Any]:
    """Verify MLX desktop binary exists; return paths checked."""
    checked = [str(p) for p in mlx_desktop_paths()]
    installed = any(Path(p).exists() for p in checked)
    linux_diag = diagnose_linux_mlx_launcher() if is_linux() else {}
    return {
        "installed": installed,
        "checked_paths": checked,
        "download_url": MLX_DOWNLOAD_URL,
        "linux_launcher": linux_diag,
    }


def xvfb_available() -> bool:
    if not is_linux():
        return False
    return bool(shutil.which("xvfb-run")) and bool(shutil.which("Xvfb"))


def linux_wrap_command(cmd: list[str]) -> list[str]:
    """Wrap command with xvfb-run on headless Linux when DISPLAY is unset."""
    if not is_linux():
        return cmd
    if os.getenv("DISPLAY", "").strip():
        return cmd
    if xvfb_available():
        return ["xvfb-run", "-a", *cmd]
    return cmd


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


def is_launcher_reachable(
    launcher_url: str | None = None,
    *,
    timeout: float = 5,
) -> bool:
    import requests

    from nextbrowser_harness.integrations.multilogin.client import LAUNCHER_BASE

    url = launcher_url or os.getenv("MULTILOGIN_LAUNCHER_URL", LAUNCHER_BASE)
    try:
        r = requests.get(url, timeout=timeout, verify=False)
        return r.status_code < 500
    except Exception:
        return False


def ensure_mlx_launcher_running(
    *,
    wait_seconds: int = 12,
    fix_linux_script: bool = True,
) -> dict[str, Any]:
    """
    Ensure MLX launcher responds before profile start.
    On Linux: optionally fix broken /opt/mlx/usr/bin/mlx script, then start desktop/agent.
    """
    report: dict[str, Any] = {
        "launcher_reachable_before": is_launcher_reachable(),
        "launcher_reachable_after": False,
        "desktop_start_attempted": False,
        "linux_fix": None,
    }
    if fix_linux_script and is_linux() and os.getenv("MULTILOGIN_SKIP_LAUNCHER_FIX", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        auto = os.getenv("MULTILOGIN_AUTO_FIX_LAUNCHER", "true").lower() in ("1", "true", "yes")
        report["linux_fix"] = fix_linux_mlx_launcher_script(apply=auto)

    if report["launcher_reachable_before"]:
        report["launcher_reachable_after"] = True
        return report

    report["desktop_start_attempted"] = try_start_mlx_desktop(wait_seconds=0)
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    report["launcher_reachable_after"] = is_launcher_reachable()
    return report


def mlx_start_desktop_hint() -> str:
    if is_windows():
        return r"Start MLX: %LOCALAPPDATA%\Multilogin X App\MLXDesktopApp.exe"
    if is_macos():
        return 'Start MLX: open -a "Multilogin X App" (install from multilogin.com if missing)'
    if is_linux():
        disp = ensure_display_linux()
        base = (
            "Start MLX: /opt/mlx/usr/bin/mlx or /opt/mlx/opt/mlx/agent.bin "
            "(set MULTILOGIN_APP_EXE). If mlx script fails: nextbrowser multilogin fix-linux-launcher"
        )
        if disp.get("needed") and not disp.get("display_ok"):
            return f"{base}. Headless Linux: {disp.get('install_hint', 'install xvfb')}"
        if disp.get("needed") and xvfb_available():
            return f"{base}. Headless: launcher runs under xvfb-run"
        return base
    return "Start the Multilogin X desktop app and ensure the launcher is on port 45001"


def try_start_mlx_desktop(*, wait_seconds: int = 8) -> bool:
    """Best-effort start MLX desktop; returns True if a start was attempted."""
    if os.getenv("MULTILOGIN_SKIP_APP_START", "").lower() in ("1", "true", "yes"):
        return False
    for path in mlx_desktop_paths():
        if not path.exists():
            continue
        try:
            if is_macos() and path.suffix == ".app":
                subprocess.Popen(["open", "-a", path.stem if path.name.endswith(".app") else str(path)])
                if wait_seconds:
                    time.sleep(wait_seconds)
                return True
            if is_linux():
                cmd: list[str]
                if path == LINUX_MLX_LAUNCHER_SCRIPT and path.is_file():
                    cmd = linux_wrap_command([str(path)])
                elif path.is_file() and os.access(path, os.X_OK):
                    cmd = linux_wrap_command([str(path)])
                else:
                    continue
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=os.environ.copy(),
                )
                if wait_seconds:
                    time.sleep(wait_seconds)
                return True
            if path.is_file() and os.access(path, os.X_OK):
                subprocess.Popen([str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if wait_seconds:
                    time.sleep(wait_seconds)
                return True
            if is_windows() and path.suffix.lower() == ".exe":
                subprocess.Popen([str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if wait_seconds:
                    time.sleep(wait_seconds)
                return True
        except OSError:
            continue
    if is_macos() and shutil.which("open"):
        try:
            subprocess.Popen(["open", "-a", "Multilogin X App"])
            if wait_seconds:
                time.sleep(wait_seconds)
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
