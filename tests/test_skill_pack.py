"""Validate bundled AgentSkills pack (YAML frontmatter, host-agnostic automation skill)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from nextbrowser_harness.platform_paths import bundled_skill_dir


FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_skill_frontmatter(skill_dir: Path | None = None) -> dict:
    root = skill_dir or bundled_skill_dir()
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    m = FRONTMATTER.match(text)
    assert m, "SKILL.md missing YAML frontmatter"
    data = yaml.safe_load(m.group(1))
    assert isinstance(data, dict)
    return data


def test_bundled_skill_layout():
    root = bundled_skill_dir()
    assert root.name == "nextbrowser-harness"
    assert (root / "SKILL.md").is_file()
    assert (root / "references" / "commands.md").is_file()
    assert (root / "references" / "browser-use-bridge.md").is_file()


def test_skill_frontmatter_agentskills():
    meta = load_skill_frontmatter()
    assert meta["name"] == "nextbrowser-harness"
    assert len(meta["description"]) >= 20
    assert re.fullmatch(r"[a-z0-9-]+", meta["name"])
    assert meta.get("license") == "MIT"
    assert "windows" in meta.get("platforms", [])


def test_skill_teaches_agent_workflow():
    root = bundled_skill_dir()
    body = (root / "SKILL.md").read_text(encoding="utf-8")
    assert "agent-run" in body
    assert "set-credentials" in body
    assert "nextbrowser login" in body
    assert "nextbrowser ui" in body
    assert "ui close" in body
    assert "agent_must_know" in body
    assert "Multilogin" in body and "CDP" in body
    assert "nextbrowser ui situation" in body
    assert "tier" in body.lower()
    assert (root / "references" / "browser-use-bridge.md").is_file()
    assert (root / "references" / "troubleshooting.md").is_file()


def test_skill_no_secret_env_prompts():
    """Hermes treats required_environment_variables as hidden secrets — only use for API keys."""
    meta = load_skill_frontmatter()
    assert "required_environment_variables" not in meta


def test_skill_pack_matches_repo():
    """skill_pack copy stays in sync with skills/ (for pip installs)."""
    from nextbrowser_harness.platform_paths import repo_root

    src = repo_root() / "skills" / "nextbrowser-harness" / "SKILL.md"
    pkg = repo_root() / "nextbrowser_harness" / "skill_pack" / "nextbrowser-harness" / "SKILL.md"
    if not pkg.is_file():
        return  # skip until sync runs in CI/release
    assert src.read_text(encoding="utf-8") == pkg.read_text(encoding="utf-8")
