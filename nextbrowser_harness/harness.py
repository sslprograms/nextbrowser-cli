from __future__ import annotations

from pathlib import Path

from nextbrowser_harness.config import HarnessConfig, resolve_config_path
from nextbrowser_harness.accounts.registry import AccountRegistry
from nextbrowser_harness.integrations.browser_use.bridge import browser_use_doctor, load_session
from nextbrowser_harness.agent_navigation import agent_automation_guide, agent_command_recipes
from nextbrowser_harness.platform_paths import cli_command_string, platform_status
from nextbrowser_harness.onboarding import onboard_from_env, onboard_interactive
from nextbrowser_harness.tiers.resolver import TierResolver
from nextbrowser_harness.workflows.accounts import AccountAutomationWorkflow
from nextbrowser_harness.workflows.browse import browse_site
from nextbrowser_harness.workflows.exec import exec_site
from nextbrowser_harness.integrations.multilogin.recommend import multilogin_recommendation
from nextbrowser_harness.workflows.scraping import ScrapingWorkflow


def _agent_fix_hint(error: str, config: HarnessConfig) -> str:
    """Actionable hint when exec/browse fails — shown to agents in JSON."""
    e = (error or "").lower()
    if "undetected-chromedriver" in e:
        return (
            "Install: pip install -e '.[playwright,undetected]' && playwright install chromium; "
            "or set NEXTBROWSER_DRIVER=playwright and use exec --browser native"
        )
    if "launcher is not reachable" in e or "connection" in e and "45001" in e:
        return "Start Multilogin X desktop app, then: nextbrowser multilogin doctor"
    if "profile_already_running" in e or "browser process is running" in e:
        return "Run: nextbrowser multilogin stop-all — then retry exec"
    if "tier 3" in e or "named account" in e or "account_required" in e:
        return (
            "Ask the user which account to use (nextbrowser account list), "
            "or create one: nextbrowser account add <name> --create-mlx"
        )
    if "credentials" in e or "placeholders" in e:
        return "Ask the user for username and password — do not use placeholders"
    if "folder_id" in e or "profile id" in e:
        return "Run: nextbrowser multilogin setup-wizard"
    if "playwright" in e and "install" in e:
        return "pip install -e '.[playwright]' && playwright install chromium"
    if config.browser == "multilogin":
        return "MLX failed — try: exec --browser native --tier 3, or fix MLX with multilogin doctor"
    return "Use full platform.cli from nextbrowser status; must be exec not scrape for clicks/JS"


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
        tier_hint = None
        if self.config.browser != "multilogin":
            tier_hint = multilogin_recommendation(self.config, url="https://www.reddit.com")
        guide = agent_automation_guide()
        for key, val in list(guide.get("commands", {}).items()):
            if isinstance(val, str) and "{cli}" in val:
                guide["commands"][key] = val.replace("{cli}", cli)
        return {
            "version": "0.1.2",
            "config": str(resolve_config_path()),
            "use_case": self.config.use_case,
            "browser": self.config.browser,
            "proxy": self.config.proxy,
            "automation": self.config.automation,
            "driver": getattr(self.config, "driver", "undetected"),
            "llm": self.config.llm_model or "(inherits from agent)",
            "tier_selection": (
                "scrape: auto tier from DB + escalate 1→2→3 until success; "
                "exec/browse tier 3: Multilogin account required (CDP); tier 1–2: native browser OK"
            ),
            "tier3_automation": guide.get("tier3_policy"),
            "accounts": AccountRegistry(self.config).agent_summary(),
            "browser_use": {
                "primary_ui": True,
                "doctor": browser_use_doctor(),
                "session": load_session(),
                "connect": f"{cli} browser-use connect --account <name>",
                "run": f"{cli} browser-use run state",
                "install_skill": f"{cli} browser-use install-skill",
            },
            "multilogin_recommendation": tier_hint,
            "platform": platform_status(),
            "agent_navigation": recipes,
            "how_to_automate": guide,
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
        profile_id: str | None = None,
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
        if not out.get("success"):
            if out.get("agent_prompt"):
                out["agent_fix"] = out["agent_prompt"]
            elif out.get("error"):
                out["agent_fix"] = _agent_fix_hint(out.get("error", ""), self.config)
        return out

    def exec(
        self,
        url: str,
        *,
        tier: int | None = None,
        profile_id: str | None = None,
        screenshot: str | None = None,
        actions: list[str] | None = None,
        steps_file: str | None = None,
        js: str | None = None,
        js_file: str | None = None,
        headless: bool | None = None,
        keep_open: bool = False,
        recipe: str | None = None,
        recipe_vars: dict[str, str] | None = None,
        element_search: str | None = None,
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
            recipe=recipe,
            recipe_vars=recipe_vars,
            element_search=element_search,
        ).to_dict()
        out["agent_mode"] = True
        out["hint"] = "Navigation via nextbrowser exec; do not spawn separate Playwright scripts."
        if not out.get("success"):
            if out.get("agent_prompt"):
                out["agent_fix"] = out["agent_prompt"]
            elif out.get("error"):
                out["agent_fix"] = _agent_fix_hint(out.get("error", ""), self.config)
        return out
