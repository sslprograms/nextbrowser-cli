"""browser_intel: URL + logged-in inference from browser-use state text."""

import pytest

from nextbrowser_harness.workflows.browser_intel import (
    agent_gates,
    build_situation_from_state_text,
    extract_current_url_from_state,
    infer_logged_in_from_state,
    infer_logged_in_with_reason,
    text_visible_in_state,
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
    assert snap["agent_gates"]["logged_in_verified"] is False


def test_auth_gate_logged_out_any_site():
    state = "Current URL: https://shop.example.com/\n[1]<a>Log in</a> Sign up"
    reason, ok = infer_logged_in_with_reason(state)
    assert ok is False
    assert "auth gate" in reason.lower() or "log in" in reason.lower()


def test_profile_url_logged_in():
    state = "Current URL: https://app.example.com/user/jake\n[1]<button>Settings</button>"
    reason, ok = infer_logged_in_with_reason(state)
    assert ok is True


def test_ebay_style_auth_url():
    state = "Current URL: https://www.ebay.com/signin/s\n[1]<input>Email"
    _, ok = infer_logged_in_with_reason(state)
    assert ok is False


def test_text_visible_in_state():
    state = "Current URL: https://reddit.com\nDroboAI is the best tool for eBay"
    assert text_visible_in_state(state, "DroboAI is the best")


def test_agent_gates_blocks_claims_when_logged_out():
    g = agent_gates(logged_in_likely=False, browser_use_ok=True)
    assert g["logged_in_verified"] is False
    assert g["safe_to_claim_comment_posted"] is False
