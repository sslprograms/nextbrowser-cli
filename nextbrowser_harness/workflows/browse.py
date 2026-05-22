"""
Interactive browser session — navigate and run simple actions (for Reddit / tier-3 sites).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from nextbrowser_harness.browser_actions import ActionSpec, BrowseActionResult, run_actions
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.browser.antidetect import browser_layer_for
from nextbrowser_harness.tiers.resolver import TierResolver


@dataclass
class BrowseResult:
    url: str
    browser: str
    tier: int
    success: bool
    title: str | None = None
    final_url: str | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    screenshot_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def browse_site(
    config: HarnessConfig,
    url: str,
    *,
    tier: int | None = None,
    profile_id: str = "reddit_default",
    headless: bool | None = None,
    screenshot: str | None = None,
    actions: list[str] | None = None,
) -> BrowseResult:
    """
    Open URL in configured browser layer and run actions.

    actions (default): goto, wait_load, title, scroll
    """
    resolver = TierResolver(Path(config.tier_cache_path))
    rec = resolver.recommended_tier(url)
    use_tier = tier or rec.tier
    if use_tier not in (1, 2, 3):
        use_tier = 3

    if use_tier == 1:
        return BrowseResult(
            url=url,
            browser=config.browser,
            tier=1,
            success=False,
            error="browse requires tier 2 or 3 (browser). Reddit is tier 3 — use --tier 3",
        )

    headful = use_tier >= 3
    if headless is None:
        headless = not headful and config.browser == "native"

    layer = browser_layer_for(config)
    session = layer.ensure_profile(profile_id)
    proxy_ep = None
    try:
        if config.proxy == "nodemaven":
            from nextbrowser_harness.layers.proxy import NodeMavenProxyLayer

            proxy_ep = NodeMavenProxyLayer.from_config(config).get_endpoint(profile_id)
        elif config.custom_proxies:
            from nextbrowser_harness.layers.proxy import CustomProxyLayer

            proxy_ep = CustomProxyLayer.from_config(config).get_endpoint(profile_id)
    except ValueError:
        pass

    action_names = actions or ["goto", "wait_load", "title", "scroll", "final_url"]
    specs = [ActionSpec.parse(a) for a in action_names]
    results: list[BrowseActionResult] = []
    ctx = None

    try:
        ctx = layer.launch_context(session, proxy=proxy_ep, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        results = run_actions(page, specs, default_url=url, screenshot=screenshot)

        title = next((r.detail for r in results if r.name == "title" and r.ok), None)
        final = next((r.detail for r in results if r.name == "final_url" and r.ok), page.url)
        blocked = page.locator("text=/captcha|prove your humanity|blocked|access denied/i").count() > 0

        if screenshot and not any(r.name == "screenshot" and r.ok for r in results):
            try:
                page.screenshot(path=screenshot, full_page=False)
            except Exception:
                pass

        return BrowseResult(
            url=url,
            browser=config.browser,
            tier=use_tier,
            success=not blocked and any(r.ok for r in results if r.name == "goto"),
            title=title,
            final_url=final,
            actions=[asdict(r) for r in results],
            error="possible block/captcha detected" if blocked else None,
            screenshot_path=screenshot,
        )
    except Exception as e:
        return BrowseResult(
            url=url,
            browser=config.browser,
            tier=use_tier,
            success=False,
            actions=[asdict(r) for r in results],
            error=str(e),
        )
    finally:
        if ctx is not None:
            try:
                if hasattr(ctx, "_harness_mlx"):
                    ctx._harness_mlx.close()
                else:
                    ctx.close()
                    if hasattr(ctx, "_harness_playwright"):
                        ctx._harness_playwright.stop()
            except Exception:
                pass
            if hasattr(layer, "stop"):
                layer.stop(profile_id)
