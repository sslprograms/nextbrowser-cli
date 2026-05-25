"""Install nextbrowser-harness skill for OpenClaw, Claude Code, Cursor, and other AgentSkills hosts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from nextbrowser_harness.agent_hosts import get_host, list_hosts
from nextbrowser_harness.platform_paths import (
    bundled_skill_dir,
    platform_status,
    resolve_openclaw_workspace,
)

SKILL_NAME = "nextbrowser-harness"

# Shared env vars for any host (inject via host config or shell profile)
DEFAULT_ENV = {
    "NEXTBROWSER_USE_CASE": "scrape",
    "NEXTBROWSER_BROWSER": "native",
    "NEXTBROWSER_DRIVER": "undetected",
    "NEXTBROWSER_AUTOMATION": "playwright",
    "NEXTBROWSER_PROXY": "none",
    "NODEMAVEN_PROXY_HOST": "",
    "NODEMAVEN_PROXY_USER": "",
    "NODEMAVEN_PROXY_PASSWORD": "",
}


def install_skill_to_dir(dest_parent: Path, *, force: bool = False) -> Path:
    src = bundled_skill_dir()
    if not src.is_dir():
        raise FileNotFoundError(f"Bundled skill not found: {src}")

    dest_parent.mkdir(parents=True, exist_ok=True)
    dest = dest_parent / SKILL_NAME

    if dest.exists():
        if not force:
            raise FileExistsError(
                f"Skill already at {dest}. Use --force to replace."
            )
        shutil.rmtree(dest)

    shutil.copytree(src, dest)
    return dest


def install_for_host(
    host_id: str,
    *,
    target: str = "managed",
    workspace: Path | None = None,
    force: bool = False,
) -> Path:
    host = get_host(host_id)
    if target == "workspace":
        ws = workspace or resolve_openclaw_workspace() or Path.cwd()
        dest_parent = host.project_skills_dir(ws)
    else:
        if host_id == "project":
            dest_parent = Path.cwd() / "skills"
        else:
            dest_parent = host.managed_skill_parent
    return install_skill_to_dir(dest_parent, force=force)


def install_all_hosts(*, target: str = "managed", workspace: Path | None = None, force: bool = False) -> list[tuple[str, Path]]:
    results: list[tuple[str, Path]] = []
    for host in list_hosts():
        if host.id == "project" and target == "managed":
            continue
        try:
            path = install_for_host(host.id, target=target, workspace=workspace, force=force)
        except FileExistsError:
            if not force:
                continue
            path = install_for_host(host.id, target=target, workspace=workspace, force=True)
        results.append((host.id, path))
    return results


def config_snippets() -> dict[str, object]:
    """Example config blocks per host."""
    return {
        "openclaw": {
            "skills": {
                "entries": {
                    SKILL_NAME: {"enabled": True, "env": DEFAULT_ENV},
                },
            },
        },
        "shell_profile": {
            "comment": "Works for Codex, Gemini CLI, generic shell agents",
            "export": DEFAULT_ENV,
        },
        "claude_code": {
            "comment": "Claude loads skills from ~/.claude/skills; set env in ~/.zshrc or use direnv",
            "paths": ["~/.claude/skills/nextbrowser-harness", ".claude/skills/nextbrowser-harness"],
        },
        "hermes": {
            "comment": "Hermes loads from ~/.hermes/skills/<category>/<skill>/",
            "skill_path": "~/.hermes/skills/browser-automation/nextbrowser-harness",
            "env_file": "~/.hermes/.env",
            "slash_command": "/nextbrowser-harness",
            "external_skill_dir": "Point Hermes at repo skills/ via config external skill directories",
            "export": DEFAULT_ENV,
        },
    }


def doctor_report() -> dict:
    st = platform_status()
    hosts = []
    for host in list_hosts():
        managed = host.managed_skill_parent / SKILL_NAME
        project = host.project_skills_dir(Path.cwd()) / SKILL_NAME
        hosts.append({
            "id": host.id,
            "name": host.name,
            "docs": host.docs_url,
            "managed_skills_dir": str(host.managed_skill_parent),
            "managed_skill_path": str(managed),
            "managed_installed": managed.is_dir() and (managed / "SKILL.md").is_file(),
            "project_skill_path": str(project),
            "project_installed": project.is_dir() and (project / "SKILL.md").is_file(),
            "config_hint": host.config_hint,
            "session_note": host.session_note,
        })
    st["agent_hosts"] = hosts
    st["config_snippets"] = config_snippets()
    return st


def print_post_install(paths: list[tuple[str, Path]]) -> str:
    from nextbrowser_harness.integrations.multilogin.platform_hints import mlx_setup_wizard_command

    lines = ["Installed nextbrowser-harness skill:"]
    for host_id, path in paths:
        lines.append(f"  [{host_id}] {path}")
    lines.extend([
        "",
        "Config examples (merge for your host):",
        json.dumps(config_snippets(), indent=2),
        "",
        "Bootstrap:",
        f"  {platform_status()['cli']} init --env",
        "",
        "Multilogin X (optional):",
        f"  {mlx_setup_wizard_command()}",
        "",
        "Use platform.cli from `nextbrowser status` as the shell prefix in any agent.",
    ])
    return "\n".join(lines)
