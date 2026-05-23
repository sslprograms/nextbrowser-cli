"""Cross-platform paths for OpenClaw, config, and CLI resolution."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def system_name() -> str:
    return platform.system().lower()  # windows, linux, darwin


def is_windows() -> bool:
    return system_name() == "windows"


def is_macos() -> bool:
    return system_name() == "darwin"


def is_linux() -> bool:
    return system_name() == "linux"


def home_dir() -> Path:
    return Path.home()


def openclaw_dir() -> Path:
    return home_dir() / ".openclaw"


def openclaw_config_path() -> Path:
    return openclaw_dir() / "openclaw.json"


def openclaw_managed_skills_dir() -> Path:
    return openclaw_dir() / "skills"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bundled_skill_dir() -> Path:
    """Bundled AgentSkills folder (repo checkout or pip wheel skill_pack)."""
    dev = repo_root() / "skills" / "nextbrowser-harness"
    if dev.is_dir() and (dev / "SKILL.md").is_file():
        return dev
    pkg = Path(__file__).resolve().parent / "skill_pack" / "nextbrowser-harness"
    if pkg.is_dir() and (pkg / "SKILL.md").is_file():
        return pkg
    raise FileNotFoundError(
        "Bundled skill missing. Expected skills/nextbrowser-harness/SKILL.md in repo "
        "or nextbrowser_harness/skill_pack/nextbrowser-harness/ in installed package."
    )


def resolve_openclaw_workspace() -> Path | None:
    """OPENCLAW_WORKSPACE or common defaults."""
    for key in ("OPENCLAW_WORKSPACE", "OPENCLAW_HOME"):
        if os.getenv(key):
            return Path(os.getenv(key, "")).expanduser().resolve()
    # OpenClaw often uses cwd as workspace when running clawhub
    cwd_skills = Path.cwd() / "skills"
    if cwd_skills.is_dir():
        return Path.cwd().resolve()
    return None


def workspace_skills_dir(workspace: Path | None = None) -> Path:
    ws = workspace or resolve_openclaw_workspace()
    if ws:
        return ws / "skills"
    return Path.cwd() / "skills"


def cli_argv() -> list[str]:
    """
    Command prefix for agents (OpenClaw exec). Prefer `nextbrowser` on PATH,
    else `python -m nextbrowser_harness.cli` (works on Linux/macOS/Windows).
    """
    if shutil.which("nextbrowser"):
        return ["nextbrowser"]
    return [sys.executable, "-m", "nextbrowser_harness.cli"]


def cli_command_string() -> str:
    return " ".join(cli_argv())


def venv_activate_hint() -> str:
    root = repo_root()
    if is_windows():
        return f"{root}\\.venv\\Scripts\\activate"
    return f"source {root}/.venv/bin/activate"


def playwright_install_hints() -> list[str]:
    hints = ["playwright install chromium"]
    if is_linux():
        hints.append("playwright install-deps chromium  # Linux: system libs (may need sudo)")
    return hints


def platform_status() -> dict:
    return {
        "os": system_name(),
        "python": sys.executable,
        "cli": cli_command_string(),
        "nextbrowser_on_path": bool(shutil.which("nextbrowser")),
        "openclaw_dir": str(openclaw_dir()),
        "openclaw_config": str(openclaw_config_path()),
        "config_exists": openclaw_config_path().exists(),
        "bundled_skill": str(bundled_skill_dir()),
        "skill_present": bundled_skill_dir().is_dir(),
    }
