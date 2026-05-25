"""Browser action parser and selector-chain helpers."""

from nextbrowser_harness.browser_actions import (
    ActionSpec,
    _looks_like_selector,
    _parse_selector_chain,
)


def test_fill_parses_as_type():
    s = ActionSpec.parse("fill:#email|user@test.com")
    assert s.type == "type"
    assert s.selectors == ["#email"]
    assert s.value == "user@test.com"


def test_type_fallback_chain():
    s = ActionSpec.parse(
        "type:#login-username input|input[name=username]|myuser"
    )
    assert s.type == "type"
    assert len(s.selectors) == 2
    assert s.value == "myuser"


def test_click_fallback_chain():
    s = ActionSpec.parse("click:button[type=submit]|faceplate-button[type=submit]")
    assert s.type == "click"
    assert len(s.selectors) == 2


def test_deep_click_alias():
    s = ActionSpec.parse("deep-click:shreddit-post >> button:has(svg[icon-name='upvote'])")
    assert s.type == "click"
    assert ">>" in s.primary_selector()


def test_wait_for_actions():
    assert ActionSpec.parse("wait-for:#login-username").type == "wait_for"
    assert ActionSpec.parse("wait-for-nav:").type == "wait_for_nav"
    assert ActionSpec.parse("wait-for-text:Success").type == "wait_for_text"


def test_inspect_and_screenshot():
    assert ActionSpec.parse("inspect:#main").type == "inspect"
    assert ActionSpec.parse("inspect-all:button").type == "inspect_all"
    assert ActionSpec.parse("screenshot:/tmp/x.png").path == "/tmp/x.png"


def test_cookie_and_logged_in():
    c = ActionSpec.parse("cookie-check:.reddit.com|reddit_session")
    assert c.type == "cookie_check"
    assert c.selector == ".reddit.com"
    assert c.value == "reddit_session"
    assert ActionSpec.parse("logged-in:reddit.com").type == "logged_in"


def test_key_action():
    assert ActionSpec.parse("key:Enter").value == "Enter"


def test_looks_like_selector():
    assert _looks_like_selector("input[name=username]")
    assert not _looks_like_selector("Pale-Accident-6750")
    assert not _looks_like_selector("user@test.com")


def test_parse_selector_chain_value():
    sels, val = _parse_selector_chain("a|b|c", value_mode=True)
    assert sels == ["a", "b"]
    assert val == "c"
