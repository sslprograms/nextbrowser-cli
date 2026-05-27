"""Back-compat shim — re-exports from agent_rules."""

from nextbrowser_harness.agent_navigation import (
    AGENT_MUST_KNOW,
    AGENT_NAVIGATION_POLICY,
    agent_automation_guide,
    agent_command_recipes,
)


def test_shim_exposes_must_know():
    assert AGENT_MUST_KNOW
    assert any("login" in line for line in AGENT_MUST_KNOW)


def test_shim_recipes_include_login_and_ui():
    recipes = agent_command_recipes()
    assert "login" in recipes
    assert "ui_state" in recipes
    assert "ui_situation" in recipes
    assert "ui_close" in recipes


def test_shim_guide_has_use_cases():
    guide = agent_automation_guide()
    assert "use_cases" in guide
    assert "accounts" in guide["use_cases"]
    assert "scrape" in guide["use_cases"]


def test_policy_string_mentions_login_and_ui():
    assert "login" in AGENT_NAVIGATION_POLICY
    assert "ui" in AGENT_NAVIGATION_POLICY
