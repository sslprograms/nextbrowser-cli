from __future__ import annotations

from pathlib import Path

from nextbrowser_harness.config import HarnessConfig, resolve_config_path
from nextbrowser_harness.agent_navigation import agent_command_recipes
from nextbrowser_harness.platform_paths import cli_command_string, platform_status
from nextbrowser_harness.onboarding import onboard_from_env, onboard_interactive
from nextbrowser_harness.tiers.resolver import TierResolver
from nextbrowser_harness.workflows.accounts import AccountAutomationWorkflow
from nextbrowser_harness.workflows.browse import browse_site
from nextbrowser_harness.workflows.exec import exec_site
from nextbrowser_harness.workflows.scraping import ScrapingWorkflow


class Harness:
    """Main orchestrator — loads config, wires workflows."""

    def __init__(self, config: HarnessConfig | None = None):
        self.config = config or HarnessConfig.load()
        self.tiers = TierResolver(
            Path(self.config.tier_cache_path),
            overrides={},
        )

    @classmethod
    def bootstrap(cls, *, interactive: bool = True, use_env: bool = False) -> Harness:
        if use_env or not resolve_config_path().exists():
            cfg = onboard_from_env() if use_env else onboard_interactive()
        else:
            cfg = HarnessConfig.load()
        return cls(cfg)

    def status(self) -> dict:
        cli = cli_command_string()
        recipes = agent_command_recipes()
        for key, val in list(recipes.items()):
            if isinstance(val, str) and "{cli}" in val:
                recipes[key] = val.replace("{cli}", cli)
        return {
            "version": "0.1.2",
            "config": str(resolve_config_path()),
            "use_case": self.config.use_case,
            "browser": self.config.browser,
            "proxy": self.config.proxy,
            "automation": self.config.automation,
            "llm": self.config.llm_model or "(inherits from agent)",
            "platform": platform_status(),
            "agent_navigation": recipes,
        }

    def scrape(self, url: str, *, tier: int | None = None) -> dict:
        wf = ScrapingWorkflow(self.config, self.tiers)
        force = int(tier) if tier in (1, 2, 3) else None  # type: ignore[arg-type]
        r = wf.scrape(url, force_tier=force)  # type: ignore[arg-type]
        return {
            "url": r.url,
            "tier": r.tier,
            "success": r.success,
            "status_code": r.status_code,
            "escalated_from": r.escalated_from,
            "preview": r.content_preview[:1500],
            "error": r.error,
        }

    def set_tier_override(self, domain: str, tier: int) -> None:
        if tier not in (1, 2, 3):
            raise ValueError("tier must be 1, 2, or 3")
        self.tiers.overrides[domain.lower()] = tier
        self.tiers._save_cache()

    def run_accounts(self, account_id: str, task: str, url: str | None = None) -> dict:
        wf = AccountAutomationWorkflow(self.config)
        return wf.run_account_task(account_id, task, url=url)

    def browse(
        self,
        url: str,
        *,
        tier: int | None = None,
        profile_id: str = "reddit_default",
        screenshot: str | None = None,
        actions: list[str] | None = None,
        headless: bool | None = None,
        steps_file: str | None = None,
        js: str | None = None,
        js_file: str | None = None,
        keep_open: bool = False,
    ) -> dict:
        out = browse_site(
            self.config,
            url,
            tier=tier,
            profile_id=profile_id,
            screenshot=screenshot,
            actions=actions,
            headless=headless,
            steps_file=steps_file,
            js=js,
            js_file=js_file,
            keep_open=keep_open,
        ).to_dict()
        out["agent_mode"] = True
        out["hint"] = "Navigation via nextbrowser browse/exec; do not spawn separate Playwright scripts."
        return out

    def exec(
        self,
        url: str,
        *,
        tier: int | None = None,
        profile_id: str = "default",
        screenshot: str | None = None,
        actions: list[str] | None = None,
        steps_file: str | None = None,
        js: str | None = None,
        js_file: str | None = None,
        headless: bool | None = None,
        keep_open: bool = False,
    ) -> dict:
        out = exec_site(
            self.config,
            url,
            tier=tier,
            profile_id=profile_id,
            screenshot=screenshot,
            actions=actions,
            steps_file=steps_file,
            js=js,
            js_file=js_file,
            headless=headless,
            keep_open=keep_open,
        ).to_dict()
        out["agent_mode"] = True
        out["hint"] = "Navigation via nextbrowser exec; do not spawn separate Playwright scripts."
        return out
