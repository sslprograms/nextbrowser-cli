import hashlib

from nextbrowser_harness.browser_actions import ActionSpec, load_steps_file
from pathlib import Path


def test_action_spec_eval():
    s = ActionSpec.parse("eval:return 1+1")
    assert s.type == "eval"
    assert s.expression == "return 1+1"


def test_action_spec_fill_delegates_to_type():
    s = ActionSpec.parse("fill:#email|a@b.com")
    assert s.type == "type"
    assert s.selectors == ["#email"]
    assert s.value == "a@b.com"


def test_action_spec_type_and_deep_click():
    t = ActionSpec.parse("type:#login-username|myuser")
    assert t.type == "type"
    assert t.selectors == ["#login-username"]
    assert t.value == "myuser"
    c = ActionSpec.parse("deep-click:shreddit-post >> button:has(svg[icon-name='upvote'])")
    assert c.type == "click"
    assert "shreddit-post" in c.primary_selector()


def test_steps_file():
    path = Path(__file__).resolve().parent.parent / "examples" / "steps-reddit.json"
    url, steps = load_steps_file(path)
    assert url == "https://www.reddit.com"
    assert len(steps) >= 5
    assert steps[0].type == "goto"
