"""Agent navigation API — browser-use skill for UI, nextbrowser for MLX CDP."""

from pathlib import Path

from nextbrowser_harness.agent_navigation import (
    agent_automation_guide,
    agent_command_recipes,
)
from nextbrowser_harness.browser_actions import load_steps_file


def test_agent_recipes_use_browser_use():
    recipes = agent_command_recipes()
    assert "browser-use" in recipes["policy"]
    assert "browser_use_connect" in recipes
    assert "connect" in recipes["browser_use_connect"]
    guide = recipes["automation"]
    assert guide["primary_ui"] == "browser-use"


def test_automation_guide_standalone():
    guide = agent_automation_guide()
    assert guide["primary_ui"] == "browser-use"
    assert guide["tier3_policy"]["connection"] == "cdp"


def test_steps_file_url_used_by_loader():
    path = Path(__file__).resolve().parent.parent / "examples" / "steps-reddit.json"
    url, steps = load_steps_file(path)
    assert url.startswith("https://")
    assert any(s.type == "eval" for s in steps)


def test_status_includes_browser_use():
    from nextbrowser_harness.harness import Harness

    st = Harness().status()
    assert "browser_use" in st
    assert st["browser_use"]["primary_ui"] is True
    assert "browser_use_connect" in st["agent_navigation"]
