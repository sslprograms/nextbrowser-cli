"""
Known agent hosts that load AgentSkills-compatible SKILL.md folders.

Spec: https://agentskills.io/
Hermes: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nextbrowser_harness.platform_paths import home_dir


@dataclass(frozen=True)
class AgentHost:
    id: str
    name: str
    docs_url: str
    managed_skills_dir: Path
    project_skills_dir: Callable[[Path], Path]
    config_hint: str
    session_note: str
    managed_subpath: str | None = None

    @property
    def managed_skill_parent(self) -> Path:
        if self.managed_subpath:
            return self.managed_skills_dir / self.managed_subpath
        return self.managed_skills_dir


def _host(
    id: str,
    name: str,
    docs_url: str,
    managed: str,
    project_parts: tuple[str, ...],
    config_hint: str,
    session_note: str,
    *,
    managed_subpath: str | None = None,
) -> AgentHost:
    return AgentHost(
        id=id,
        name=name,
        docs_url=docs_url,
        managed_skills_dir=home_dir() / managed,
        project_skills_dir=lambda ws, parts=project_parts: ws.joinpath(*parts),
        config_hint=config_hint,
        session_note=session_note,
        managed_subpath=managed_subpath,
    )


# Registry of hosts similar to OpenClaw (CLI + SKILL.md + shell exec)
AGENT_HOSTS: dict[str, AgentHost] = {
    "hermes": _host(
        "hermes",
        "Hermes Agent",
        "https://hermes-agent.nousresearch.com/docs/user-guide/features/skills",
        ".hermes/skills",
        (".hermes", "skills", "browser-automation"),
        "~/.hermes/.env or hermes setup — export NEXTBROWSER_*; or point external skill dir at repo skills/",
        "New Hermes session after install; slash command /nextbrowser-harness or hermes --skills nextbrowser-harness",
        managed_subpath="browser-automation",
    ),
    "openclaw": _host(
        "openclaw",
        "OpenClaw",
        "https://openclawx.cloud/en/tools/skills",
        ".openclaw/skills",
        ("skills",),
        "~/.openclaw/openclaw.json → skills.entries.nextbrowser-harness.env",
        "Start a new OpenClaw session after install.",
    ),
    "claude": _host(
        "claude",
        "Claude Code",
        "https://code.claude.com/docs/en/skills",
        ".claude/skills",
        (".claude", "skills"),
        "~/.claude/settings.json or project .claude/ — set env in shell profile or skill scripts",
        "Restart Claude Code or start a new session; skills are watched live.",
    ),
    "codex": _host(
        "codex",
        "OpenAI Codex / CLI agents",
        "https://agentskills.io/",
        ".codex/skills",
        (".codex", "skills"),
        "Export NEXTBROWSER_* in shell before running codex",
        "New session after installing skill.",
    ),
    "gemini": _host(
        "gemini",
        "Gemini CLI",
        "https://agentskills.io/",
        ".gemini/skills",
        (".gemini", "skills"),
        "Export env vars in ~/.bashrc or project .env",
        "New session after install.",
    ),
    "opencode": _host(
        "opencode",
        "OpenCode",
        "https://agentskills.io/",
        ".config/opencode/skills",
        (".opencode", "skills"),
        "Check OpenCode docs for skills directory",
        "Reload OpenCode after install.",
    ),
    "cursor": _host(
        "cursor",
        "Cursor",
        "https://docs.cursor.com/",
        ".cursor/skills",
        (".cursor", "skills"),
        "Cursor Settings → Rules, or project .cursor/skills/; env via .env or MCP host",
        "Reload Cursor window after adding skill.",
    ),
    "continue": _host(
        "continue",
        "Continue",
        "https://docs.continue.dev/",
        ".continue/skills",
        (".continue", "skills"),
        "Continue config.yaml or ~/.continue/.env for NEXTBROWSER_*",
        "Reload Continue after install.",
    ),
    "roo": _host(
        "roo",
        "Roo Code",
        "https://docs.roocode.com/",
        ".roo/skills",
        (".roo", "skills"),
        "Roo settings or project .roo/skills/; export NEXTBROWSER_* in shell",
        "Reload VS Code window after install.",
    ),
    "windsurf": _host(
        "windsurf",
        "Windsurf / Cline",
        "https://docs.windsurf.com/",
        ".codeium/windsurf/skills",
        (".windsurf", "skills"),
        "May use .windsurf/skills or global; check Windsurf skills docs",
        "Reload IDE after install.",
    ),
    "kilocode": _host(
        "kilocode",
        "Kilo Code",
        "https://kilocode.ai/docs/",
        ".kilocode/skills",
        (".kilocode", "skills"),
        "Export NEXTBROWSER_* in shell or project .env",
        "Reload IDE after install.",
    ),
    "project": _host(
        "project",
        "Generic project skills/",
        "https://agentskills.io/",
        "skills",  # cwd-relative managed won't be used
        ("skills",),
        "Export NEXTBROWSER_* in environment; any agent with shell access",
        "Point agent at ./skills/nextbrowser-harness/SKILL.md",
    ),
}


def list_hosts() -> list[AgentHost]:
    seen: set[str] = set()
    out: list[AgentHost] = []
    for h in AGENT_HOSTS.values():
        if h.id in seen:
            continue
        if h.id == "claude-code":
            continue  # skip duplicate of claude paths
        seen.add(h.id)
        out.append(h)
    return sorted(out, key=lambda x: x.name)


def get_host(host_id: str) -> AgentHost:
    key = host_id.lower().replace("_", "-")
    aliases = {
        "claude-code": "claude",
        "open-claw": "openclaw",
        "hermes-agent": "hermes",
        "cline": "windsurf",
        "kilo": "kilocode",
    }
    key = aliases.get(key, key)
    if key not in AGENT_HOSTS:
        ids = ", ".join(sorted(h.id for h in list_hosts()))
        raise KeyError(f"Unknown host {host_id!r}. Choose from: {ids}, all")
    return AGENT_HOSTS[key]
