"""Agent prompt assembly and runner init tests."""

from nextbrowser_harness.agent.prompts.system_prompt import SYSTEM_PROMPT
from nextbrowser_harness.agent.prompts.interactive_elements import INTERACTIVE_ELEMENTS_GUIDANCE
from nextbrowser_harness.agent.prompts.captcha import CAPTCHA_PROMPT
from nextbrowser_harness.agent.prompts.tabs import TAB_GUIDANCE
from nextbrowser_harness.agent.prompts.approval import APPROVAL_PROMPT
from nextbrowser_harness.agent.prompts.account_context import account_context_prompt
from nextbrowser_harness.agent.runner import _build_audit_trail, _build_system_prompt


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
    assert "logged in" in prompt.lower()
    assert "Multilogin" in prompt
    assert "placeholder" in prompt.lower()


def test_account_context_prompt_not_logged_in():
    prompt = account_context_prompt("alice", logged_in=False)
    assert "NOT logged in" in prompt


def test_account_context_with_credentials():
    prompt = account_context_prompt(
        "alice",
        logged_in=False,
        has_credentials=True,
        logged_in_live=False,
    )
    assert "sensitive_data" in prompt
    assert "MUST" in prompt


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
    assert "logged in" in extend.lower()


def test_build_system_prompt_with_captcha():
    _, extend = _build_system_prompt(enable_captcha=True)
    assert "captcha" in extend.lower()


def test_build_system_prompt_with_approval():
    _, extend = _build_system_prompt(enable_approval=True)
    assert "should_be_approved" in extend


def test_reddit_guidance_injected_for_reddit_task():
    from nextbrowser_harness.agent.runner import _build_system_prompt, _needs_reddit_guidance

    assert _needs_reddit_guidance(task="comment on reddit post", url="https://reddit.com/r/test")
    _, extend = _build_system_prompt(task="comment on reddit", url="https://reddit.com")
    assert "reddit_automation" in extend.lower()


def test_build_system_prompt_has_execution_verification():
    _, extend = _build_system_prompt()
    assert "execution_verification" in extend
    assert "Never state an action as completed" in extend


def test_build_audit_trail_marks_verified_steps():
    class FakeResult:
        def __init__(self, error=None, extracted_content=""):
            self.error = error
            self.extracted_content = extracted_content

    class FakeModelOutput:
        def __init__(self, action):
            self.action = action

    class FakeBrowserState:
        def __init__(self, url):
            self.url = url

    class FakeStep:
        def __init__(self, action, url, error=None):
            self.model_output = FakeModelOutput(action)
            self.browser_state = FakeBrowserState(url)
            self.result = [FakeResult(error=error, extracted_content="ok")]

    class FakeHistory:
        def __init__(self, steps):
            self.history = steps

    history = FakeHistory(
        [
            FakeStep([{"go_to_url": {"url": "https://a.com"}}], "https://a.com"),
            FakeStep([{"click_element_by_index": {"index": 3}}], "https://a.com/page", error=None),
            FakeStep([{"input_text": {"index": 1, "text": "x"}}], "https://a.com/page", error="Element not found"),
        ]
    )
    trail = _build_audit_trail(history)
    assert len(trail) == 3
    assert trail[0]["verified"] is True
    assert trail[1]["url_changed"] is True
    assert trail[2]["verified"] is False
    assert "Element not found" in trail[2]["error"]
