"""Agent navigation API — must-know rules exposed in status."""

from pathlib import Path

from nextbrowser_harness.agent_navigation import (
    AGENT_MUST_KNOW,
    agent_automation_guide,
    agent_command_recipes,
)
from nextbrowser_harness.browser_actions import load_steps_file


def test_agent_must_know_covers_keep_alive_and_chain():
    text = " ".join(AGENT_MUST_KNOW).lower()
    assert "chain" in text
    assert "disconnect" in text
    assert "stay open" in text or "stays open" in text
    assert "create-mlx" in text
    assert "browser-use" in text


def test_agent_recipes_include_chain_and_disconnect():
    recipes = agent_command_recipes()
    assert "agent_must_know" in recipes
    assert "chain" in recipes["browser_use_chain_login"]
    assert "disconnect" in recipes["browser_use_disconnect"]


def test_status_includes_agent_must_know():
    from nextbrowser_harness.harness import Harness

    st = Harness().status()
    assert "agent_must_know" in st
    assert len(st["agent_must_know"]) >= 5
    assert st["browser_use"].get("chain_login")
    assert st["browser_use"].get("disconnect")
    joined = " ".join(st["agent_must_know"]).lower()
    assert "chain" in joined


def test_steps_file_url_used_by_loader():
    path = Path(__file__).resolve().parent.parent / "examples" / "steps-reddit.json"
    url, steps = load_steps_file(path)
    assert url.startswith("https://")
    assert any(s.type == "eval" for s in steps)
