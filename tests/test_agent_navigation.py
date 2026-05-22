"""Agent navigation API matches docs — CLI recipes, steps file, no duplicate browse logic."""

from pathlib import Path

from nextbrowser_harness.agent_navigation import agent_command_recipes
from nextbrowser_harness.browser_actions import load_steps_file


def test_agent_recipes_include_exec_not_playwright():
    recipes = agent_command_recipes()
    assert "exec" in recipes["navigate"]
    assert "Playwright Python" in recipes["policy"]


def test_steps_file_url_used_by_loader():
    path = Path(__file__).resolve().parent.parent / "examples" / "steps-reddit.json"
    url, steps = load_steps_file(path)
    assert url.startswith("https://")
    assert any(s.type == "eval" for s in steps)


def test_status_includes_agent_navigation():
    from nextbrowser_harness.harness import Harness

    st = Harness().status()
    assert "agent_navigation" in st
    assert "inject_js" in st["agent_navigation"]
