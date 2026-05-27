"""
AI-driven browser agent that runs browser-use over a Multilogin CDP session.

Architecture (ported from next-browser-main/task-runner):
  1. Start or reuse an MLX profile (CDP URL)
  2. Create a browser-use BrowserSession connected to CDP
  3. Create a browser-use Agent with system prompt + task
  4. Run the step loop: agent.take_step() until done or max_steps
  5. Return structured result

The agent uses the same prompt system as next-browser-main:
  - System prompt with indexed elements, reasoning rules, action format
  - Interactive element guidance for platform-specific patterns
  - Captcha, tab, and approval prompts appended as extensions
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from nextbrowser_harness.accounts.registry import AccountRegistry, Tier3AccountError
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.browser_use.bridge import connect_account, load_session
from nextbrowser_harness.integrations.multilogin.session import mark_keep_alive

from .prompts.account_context import account_context_prompt
from .prompts.captcha import CAPTCHA_PROMPT
from .prompts.interactive_elements import INTERACTIVE_ELEMENTS_GUIDANCE
from .prompts.system_prompt import SYSTEM_PROMPT
from .prompts.tabs import TAB_GUIDANCE

logger = logging.getLogger(__name__)

MAX_STEPS = int(os.getenv("NEXTBROWSER_AGENT_MAX_STEPS", "100"))
MAX_ACTIONS_PER_STEP = int(os.getenv("NEXTBROWSER_AGENT_MAX_ACTIONS", "10"))
MAX_FAILURES = int(os.getenv("NEXTBROWSER_AGENT_MAX_FAILURES", "10"))
LLM_TIMEOUT = int(os.getenv("NEXTBROWSER_AGENT_LLM_TIMEOUT", "150"))


@dataclass
class AgentRunResult:
    success: bool
    account_id: str
    task: str
    steps_taken: int = 0
    final_text: str = ""
    files: list[str] = field(default_factory=list)
    cdp_url: str = ""
    error: str | None = None
    agent_prompt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_llm(model_name: str):
    """Create an LLM instance compatible with browser-use."""
    if model_name.startswith("gpt-"):
        from browser_use.llm import ChatOpenAI

        return ChatOpenAI(model=model_name, timeout=LLM_TIMEOUT)
    elif model_name.startswith("gemini-"):
        from browser_use.llm import ChatGoogle

        return ChatGoogle(model=model_name)
    elif model_name.startswith("claude-"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name, timeout=LLM_TIMEOUT)
    else:
        from browser_use.llm import ChatOpenAI

        return ChatOpenAI(model=model_name, timeout=LLM_TIMEOUT)


def _build_system_prompt(
    account_id: str | None = None,
    site: str = "",
    logged_in: bool = False,
    display_name: str = "",
    enable_captcha: bool = False,
    enable_approval: bool = False,
) -> tuple[str, str]:
    """Return (override_system_message, extend_system_message)."""
    extensions = [INTERACTIVE_ELEMENTS_GUIDANCE, TAB_GUIDANCE]

    if account_id:
        extensions.append(
            account_context_prompt(
                account_id, site=site, logged_in=logged_in, display_name=display_name
            )
        )

    if enable_captcha:
        extensions.append(CAPTCHA_PROMPT)

    if enable_approval:
        from .prompts.approval import APPROVAL_PROMPT

        extensions.append(APPROVAL_PROMPT)

    return SYSTEM_PROMPT, "\n".join(extensions)


async def _run_agent_async(
    cdp_url: str,
    task: str,
    model_name: str,
    *,
    account_id: str = "",
    site: str = "",
    logged_in: bool = False,
    display_name: str = "",
    enable_captcha: bool = False,
    enable_approval: bool = False,
    max_steps: int = MAX_STEPS,
    downloads_dir: str | None = None,
) -> AgentRunResult:
    """Core async agent loop — connects to CDP and runs browser-use Agent."""
    from browser_use import Agent, BrowserProfile, BrowserSession

    override_prompt, extend_prompt = _build_system_prompt(
        account_id=account_id,
        site=site,
        logged_in=logged_in,
        display_name=display_name,
        enable_captcha=enable_captcha,
        enable_approval=enable_approval,
    )

    dl_dir = downloads_dir or os.path.join(
        os.path.expanduser("~"), ".nextbrowser", "downloads", str(int(time.time()))
    )
    os.makedirs(dl_dir, exist_ok=True)

    browser_session = BrowserSession(
        cdp_url=cdp_url,
        browser_profile=BrowserProfile(
            highlight_elements=False,
            downloads_path=dl_dir,
        ),
        no_viewport=True,
    )

    llm = _get_llm(model_name)

    agent = Agent(
        task=task,
        llm=llm,
        browser_session=browser_session,
        override_system_message=override_prompt,
        extend_system_message=extend_prompt,
        max_failures=MAX_FAILURES,
        max_history_items=100,
        llm_timeout=LLM_TIMEOUT,
    )

    result = AgentRunResult(
        success=False,
        account_id=account_id,
        task=task,
        cdp_url=cdp_url,
    )

    try:
        history = await agent.run(max_steps=max_steps)
        result.steps_taken = len(history.history) if history else 0
        result.success = history.is_successful() if history else False
        result.final_text = history.final_result() if history else ""
    except Exception as e:
        logger.error(f"Agent run failed: {e}", exc_info=True)
        result.error = str(e)

    return result


def run_agent(
    config: HarnessConfig,
    task: str,
    *,
    account_id: str | None = None,
    model: str | None = None,
    url: str | None = None,
    enable_captcha: bool = False,
    enable_approval: bool = False,
    max_steps: int = MAX_STEPS,
    headless: bool = False,
) -> AgentRunResult:
    """
    Synchronous entry point — start MLX profile, connect CDP, run the AI agent.

    If account_id is provided, uses Multilogin. Otherwise uses any existing
    browser-use session (if available).
    """
    model_name = model or os.getenv("NEXTBROWSER_LLM_MODEL", "gpt-4o")

    site = ""
    logged_in = False
    display_name = ""
    cdp_url = ""

    if account_id:
        try:
            conn = connect_account(config, account_id, headless=headless)
            cdp_url = conn["cdp_url"]
        except Tier3AccountError as e:
            return AgentRunResult(
                success=False,
                account_id=account_id or "",
                task=task,
                error=str(e),
                agent_prompt=e.agent_prompt,
            )
        except Exception as e:
            return AgentRunResult(
                success=False,
                account_id=account_id or "",
                task=task,
                error=f"MLX connect failed: {e}",
                agent_prompt="Check `nextbrowser multilogin doctor` then retry.",
            )

        acc = AccountRegistry(config).get(account_id)
        if acc:
            site = acc.site
            logged_in = acc.logged_in
            display_name = acc.display_name
    else:
        sess = load_session()
        if sess and sess.get("cdp_url"):
            cdp_url = sess["cdp_url"]
            account_id = sess.get("account_id", "")
        else:
            return AgentRunResult(
                success=False,
                account_id="",
                task=task,
                error="No CDP session. Run `nextbrowser login <account> --url <url>` first.",
            )

    if url:
        task = f"First navigate to {url}, then: {task}"

    return asyncio.run(
        _run_agent_async(
            cdp_url,
            task,
            model_name,
            account_id=account_id or "",
            site=site,
            logged_in=logged_in,
            display_name=display_name,
            enable_captcha=enable_captcha,
            enable_approval=enable_approval,
            max_steps=max_steps,
        )
    )
