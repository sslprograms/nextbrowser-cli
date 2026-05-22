from __future__ import annotations

import asyncio
import os

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.automation.base import AutomationResult
from nextbrowser_harness.layers.automation.playwright_adapter import PlaywrightAutomationLayer


class BrowserUseLayer:
    """Browser Use — default automation framework (optional dependency)."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self._fallback = PlaywrightAutomationLayer.from_config(config)

    @classmethod
    def from_config(cls, config: HarnessConfig) -> BrowserUseLayer:
        return cls(config)

    def run_task(self, task: str, *, url: str | None = None, profile_id: str = "default") -> AutomationResult:
        try:
            from browser_use import Agent, Browser, ChatAnthropic, ChatOpenAI  # type: ignore
        except ImportError:
            return AutomationResult(
                success=False,
                output="",
                error="browser-use not installed. pip install 'nextbrowser-harness[browser-use]'",
            )

        llm = self._resolve_llm(ChatAnthropic, ChatOpenAI)
        if llm is None:
            return self._fallback.run_task(task, url=url, profile_id=profile_id)

        async def _run():
            browser = Browser()
            agent = Agent(task=task if not url else f"{task} Start at {url}", llm=llm, browser=browser)
            history = await agent.run()
            return str(history)[-4000:]

        try:
            output = asyncio.run(_run())
            return AutomationResult(success=True, output=output)
        except Exception as e:
            return AutomationResult(success=False, output="", error=str(e))

    def _resolve_llm(self, ChatAnthropic, ChatOpenAI):
        model = self.config.llm_model or os.getenv("NEXTBROWSER_LLM_MODEL")
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model=model or "claude-sonnet-4-20250514")
        if os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(model=model or "gpt-4o")
        return None
