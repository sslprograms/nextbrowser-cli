"""Agent prompt assembly and runner init tests."""

from nextbrowser_harness.agent.prompts.system_prompt import SYSTEM_PROMPT
from nextbrowser_harness.agent.prompts.interactive_elements import INTERACTIVE_ELEMENTS_GUIDANCE
from nextbrowser_harness.agent.prompts.captcha import CAPTCHA_PROMPT
from nextbrowser_harness.agent.prompts.tabs import TAB_GUIDANCE
from nextbrowser_harness.agent.prompts.approval import APPROVAL_PROMPT
from nextbrowser_harness.agent.prompts.account_context import account_context_prompt
from nextbrowser_harness.agent.runner import _build_system_prompt


def test_system_prompt_has_core_sections():
    for section in [
        "<browser_state>",
        "<browser_vision>",
        "<browser_rules>",
        "<reasoning_rules>",
        "<action_rules>",
        "<output>",
        "evaluation_previous_goal",
        "click_element_by_index",
    ]:
        assert section in SYSTEM_PROMPT, f"Missing section: {section}"


def test_interactive_elements_has_platform_patterns():
    text = INTERACTIVE_ELEMENTS_GUIDANCE.lower()
    assert "facebook" in text
    assert "linkedin" in text
    assert "twitter" in text or "x interactions" in text
    assert "contenteditable" in text
    assert "send_keys" in text


def test_captcha_prompt_mentions_recaptcha():
    assert "recaptcha" in CAPTCHA_PROMPT.lower()
    assert "hcaptcha" in CAPTCHA_PROMPT.lower()
    assert "turnstile" in CAPTCHA_PROMPT.lower()


def test_tab_guidance_limits_tabs():
    assert "5 or fewer" in TAB_GUIDANCE


def test_approval_prompt_covers_social():
    text = APPROVAL_PROMPT.lower()
    assert "should_be_approved" in text
    assert "reddit" in text
    assert "linkedin" in text


def test_account_context_prompt_includes_details():
    prompt = account_context_prompt(
        "reddit_main",
        site="reddit.com",
        logged_in=True,
        display_name="Reddit Main",
    )
    assert "reddit_main" in prompt
    assert "reddit.com" in prompt
    assert "already logged in" in prompt
    assert "Multilogin" in prompt
    assert "placeholder" in prompt.lower()


def test_account_context_prompt_not_logged_in():
    prompt = account_context_prompt("alice", logged_in=False)
    assert "NOT logged in" in prompt


def test_build_system_prompt_basic():
    override, extend = _build_system_prompt()
    assert override == SYSTEM_PROMPT
    assert "interactive_element_guidance" in extend.lower()
    assert "tab_management" in extend.lower()


def test_build_system_prompt_with_account():
    override, extend = _build_system_prompt(
        account_id="bob",
        site="twitter.com",
        logged_in=True,
    )
    assert "bob" in extend
    assert "twitter.com" in extend
    assert "already logged in" in extend


def test_build_system_prompt_with_captcha():
    _, extend = _build_system_prompt(enable_captcha=True)
    assert "captcha" in extend.lower()


def test_build_system_prompt_with_approval():
    _, extend = _build_system_prompt(enable_approval=True)
    assert "should_be_approved" in extend
