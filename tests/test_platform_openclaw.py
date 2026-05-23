from nextbrowser_harness.agent_setup import config_snippets, install_for_host
from nextbrowser_harness.openclaw_setup import install_skill
from nextbrowser_harness.platform_paths import (
    bundled_skill_dir,
    cli_argv,
    platform_status,
)


def test_bundled_skill_exists():
    assert bundled_skill_dir().is_dir()
    assert (bundled_skill_dir() / "SKILL.md").is_file()


def test_cli_argv_is_non_empty():
    argv = cli_argv()
    assert len(argv) >= 2 or argv == ["nextbrowser"]


def test_platform_status_keys():
    st = platform_status()
    assert "os" in st
    assert st["os"] in ("windows", "linux", "darwin", "java", "freebsd") or st["os"]
    assert "cli" in st
    assert "skill_present" in st


def test_install_skill_managed(tmp_path, monkeypatch):
    from nextbrowser_harness.agent_hosts import AgentHost

    fake = AgentHost(
        "openclaw", "OpenClaw", "", tmp_path / "skills", lambda ws: ws / "skills", "", ""
    )
    monkeypatch.setattr("nextbrowser_harness.agent_setup.get_host", lambda _: fake)
    dest = install_skill(target="managed", force=True)
    assert dest.name == "nextbrowser-harness"
    assert (dest / "SKILL.md").exists()


def test_openclaw_snippet_structure():
    snip = config_snippets()["openclaw"]
    assert "nextbrowser-harness" in snip["skills"]["entries"]


def test_list_hosts_includes_claude():
    from nextbrowser_harness.agent_hosts import list_hosts

    ids = {h.id for h in list_hosts()}
    assert "openclaw" in ids
    assert "claude" in ids
    assert "cursor" in ids
    assert "hermes" in ids


def test_hermes_managed_subpath():
    from nextbrowser_harness.agent_hosts import get_host

    host = get_host("hermes")
    assert host.managed_subpath == "browser-automation"
    assert host.managed_skill_parent.name == "browser-automation"
