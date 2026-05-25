"""Agent navigation API — one automation model for all hosts."""

from pathlib import Path

from nextbrowser_harness.agent_navigation import (
    agent_automation_guide,
    agent_command_recipes,
)
from nextbrowser_harness.browser_actions import load_steps_file


def test_agent_recipes_policy_and_indexed_flow():
    recipes = agent_command_recipes()
    assert "Playwright" in recipes["policy"]
    assert "state" in recipes["open_and_list_elements"]
    assert "account" in recipes["open_and_list_elements"]
    assert recipes["automation"]["tier3_policy"]["connection"] == "cdp"
    assert "click:INDEX" in recipes["click_by_index"]
    guide = recipes["automation"]
    assert "workflow" in guide
    assert any("state" in step for step in guide["workflow"])


def test_automation_guide_standalone():
    guide = agent_automation_guide()
    assert guide["element_search"]["default"] == "indexed"
    assert "never" in guide


def test_steps_file_url_used_by_loader():
    path = Path(__file__).resolve().parent.parent / "examples" / "steps-reddit.json"
    url, steps = load_steps_file(path)
    assert url.startswith("https://")
    assert any(s.type == "eval" for s in steps)


def test_status_includes_agent_navigation_and_how_to_automate():
    from nextbrowser_harness.harness import Harness

    st = Harness().status()
    assert "agent_navigation" in st
    assert "how_to_automate" in st
    assert st["how_to_automate"]["element_search"]["default"] == "indexed"
    assert "open_and_list_elements" in st["agent_navigation"]
    assert "tier3_automation" in st
    assert st["tier3_automation"]["connection"] == "cdp"
