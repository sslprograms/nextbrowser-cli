"""
Agent-facing browser automation: inject JS, run step files, click/fill — native or Multilogin.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from nextbrowser_harness.browser_actions import ActionSpec, load_steps_file, run_actions
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.browser.antidetect import browser_layer_for
from nextbrowser_harness.tiers.resolver import TierResolver
from nextbrowser_harness.workflows.browser_result import BrowseResult


def exec_site(
    config: HarnessConfig,
    url: str,
    *,
    tier: int | None = None,
    profile_id: str = "default",
    headless: bool | None = None,
    screenshot: str | None = None,
    actions: list[str | dict] | None = None,
    steps_file: str | Path | None = None,
    js: str | None = None,
    js_file: str | Path | None = None,
    keep_open: bool = False,
) -> BrowseResult:
    """
    Open browser, run automation steps, return JSON-friendly result for agents.
    """
    resolver = TierResolver(Path(config.tier_cache_path))
    rec = resolver.recommended_tier(url)
    use_tier = tier or rec.tier
    if use_tier not in (2, 3):
        use_tier = 3

    specs: list[ActionSpec] = []
    if steps_file:
        steps_url, steps = load_steps_file(steps_file)
        if steps_url:
            url = steps_url
        specs.extend(steps)
    if js_file:
        specs.append(ActionSpec.parse(f"jsfile:{js_file}"))
    if js:
        specs.append(ActionSpec.parse(f"eval:{js}"))
    for raw in actions or []:
        specs.append(ActionSpec.parse(raw))

    if not specs:
        specs = [
            ActionSpec.parse("goto"),
            ActionSpec.parse("wait_load"),
            ActionSpec.parse("title"),
            ActionSpec.parse("final_url"),
        ]
    elif specs[0].type != "goto":
        specs.insert(0, ActionSpec.parse("goto"))

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

    ctx = None
    results = []
    try:
        ctx = layer.launch_context(session, proxy=proxy_ep, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        results = run_actions(page, specs, default_url=url, screenshot=screenshot)

        if screenshot and not any(r.name == "screenshot" and r.ok for r in results):
            try:
                page.screenshot(path=screenshot, full_page=False)
            except Exception:
                pass

        title = next((r.detail for r in results if r.name == "title" and r.ok), None)
        final = next((r.detail for r in results if r.name == "final_url" and r.ok), page.url)
        blocked = page.locator("text=/captcha|prove your humanity|blocked|access denied/i").count() > 0
        optional = {"reddit_feed_check", "wait_load"}
        required_ok = [r for r in results if r.name not in optional]
        navigated = any(r.ok for r in results if r.name in ("goto", "eval", "jsfile"))

        return BrowseResult(
            url=url,
            browser=config.browser,
            tier=use_tier,
            success=not blocked and navigated and (not required_ok or all(r.ok for r in required_ok)),
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
            actions=[asdict(r) for r in results] if results else [],
            error=str(e),
        )
    finally:
        if not keep_open and ctx is not None:
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
