import hashlib

from nextbrowser_harness.browser_actions import ActionSpec, load_steps_file
from pathlib import Path


def test_action_spec_eval():
    s = ActionSpec.parse("eval:return 1+1")
    assert s.type == "eval"
    assert s.expression == "return 1+1"


def test_action_spec_fill():
    s = ActionSpec.parse("fill:#email|a@b.com")
    assert s.type == "fill"
    assert s.selector == "#email"
    assert s.value == "a@b.com"


def test_steps_file():
    path = Path(__file__).resolve().parent.parent / "examples" / "steps-reddit.json"
    steps = load_steps_file(path)
    assert len(steps) >= 5
    assert steps[0].type == "goto"
