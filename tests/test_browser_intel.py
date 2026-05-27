"""browser_intel: URL + logged-in inference from browser-use state text."""

import pytest

from nextbrowser_harness.workflows.browser_intel import (
    build_situation_from_state_text,
    extract_current_url_from_state,
    infer_logged_in_from_state,
    infer_logged_in_with_reason,
)


def test_extract_current_url():
    s = "Current URL: https://x.com/foo\nInteractive Elements:"
    assert extract_current_url_from_state(s) == "https://x.com/foo"


def test_infer_logged_in_sign_in_only():
    s = '[1]<button aria-label="Sign In">Login</button>\nCurrent URL: https://example.com/'
    assert infer_logged_in_from_state(s) is False


@pytest.mark.parametrize(
    "text,expect",
    [
        ("Current URL: https://app/foo\n*[2]<button>Log out</button>", True),
        ("Current URL: https://reddit.com/login", False),
    ],
)
def test_infer_param(text, expect):
    assert infer_logged_in_from_state(text) == expect


def test_infer_uncertain_returns_none():
    assert infer_logged_in_from_state("Interactive Elements:\nSome text.") is None


def test_infer_with_reason_always_has_string():
    r, v = infer_logged_in_with_reason("")
    assert isinstance(r, str)
    assert v is None


def test_build_situation_registry_mismatch():
    state = "Current URL: https://reddit.com/login\n[1]<a>sign in</a>"
    snap = build_situation_from_state_text(
        state,
        account_id="r1",
        registry_logged_in=True,
        browser_use_exit_code=0,
    ).to_dict()
    assert snap["logged_in_registry"] is True
    assert snap["logged_in_likely"] is False
    assert any("expired" in h.lower() or "wrong tab" in h.lower() for h in snap["hints"])
