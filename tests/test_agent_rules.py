"""Single source of truth for agent guidance."""

from nextbrowser_harness import agent_rules


def test_must_know_includes_keep_alive_and_login():
    text = " ".join(agent_rules.MUST_KNOW).lower()
    assert "browser-use" in text
    assert "login" in text
    assert "ui situation" in text
    assert "ui close" in text or "disconnect" in text
    assert "placeholder" in text or "ask the user" in text


def test_render_substitutes_cli_prefix():
    rendered = agent_rules.render("py -m nextbrowser_harness.cli")
    joined = " ".join(rendered["must_know"])
    assert "py -m nextbrowser_harness.cli" in joined
    assert "{cli}" not in joined
    commands = rendered["commands"]
    assert "{cli}" not in commands["login"]
    assert "situation" in commands["ui_situation"].lower()


def test_guide_contains_use_cases_and_stack():
    guide = agent_rules.automation_guide()
    assert "accounts" in guide["use_cases"]
    assert "scrape" in guide["use_cases"]
    assert "multilogin" in guide["stack"]["browser"]
    assert "browser_use" in guide["stack"]["automation"]


def test_backcompat_shim_exports_old_names():
    from nextbrowser_harness import agent_navigation as an

    assert an.AGENT_MUST_KNOW == agent_rules.MUST_KNOW
    assert callable(an.agent_command_recipes)
    assert callable(an.agent_automation_guide)


def test_status_surfaces_must_know_and_commands():
    from nextbrowser_harness.harness import Harness

    st = Harness().status()
    assert st["spec"].startswith("Nextbrowser Harness MVP")
    assert "agent_must_know" in st
    assert "commands" in st
    assert "stack" in st
    assert "login" in st["commands"]
