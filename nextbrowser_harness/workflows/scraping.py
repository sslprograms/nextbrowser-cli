from __future__ import annotations

from dataclasses import dataclass

import requests

from nextbrowser_harness.config import HarnessConfig, TierLevel
from nextbrowser_harness.layers.browser.antidetect import browser_layer_for
from nextbrowser_harness.layers.proxy import CustomProxyLayer, NodeMavenProxyLayer
from nextbrowser_harness.tiers.resolver import TierResolver


@dataclass
class ScrapeResult:
    url: str
    tier: TierLevel
    success: bool
    status_code: int | None
    content_preview: str
    error: str | None = None
    escalated_from: TierLevel | None = None


class ScrapingWorkflow:
    """
    Three-tier scraping with curated DB lookup, automatic escalation, and cache.
    Tier 1: HTTP requests. Tier 2: headless browser. Tier 3: headful anti-detect.
    """

    def __init__(self, config: HarnessConfig, resolver: TierResolver):
        self.config = config
        self.resolver = resolver
        self._proxy = self._build_proxy()

    def _build_proxy(self):
        if self.config.proxy == "nodemaven":
            try:
                return NodeMavenProxyLayer.from_config(self.config)
            except ValueError:
                return None
        if self.config.custom_proxies:
            return CustomProxyLayer.from_config(self.config)
        return None

    def _browser_layer(self):
        return browser_layer_for(self.config)

    def scrape(
        self,
        url: str,
        *,
        force_tier: TierLevel | None = None,
        max_bytes: int = 50_000,
    ) -> ScrapeResult:
        rec = self.resolver.recommended_tier(url)
        start: TierLevel = force_tier or rec.tier  # type: ignore[assignment]
        domain = rec.domain
        last_error = None
        escalated_from = None

        for i, tier in enumerate(self.resolver.escalation_order(start)):
            if i > 0:
                escalated_from = self.resolver.escalation_order(start)[i - 1]
            result = self._run_tier(url, tier, max_bytes=max_bytes)
            if result.success:
                self.resolver.remember_success(domain, tier)
                result.escalated_from = escalated_from  # type: ignore[assignment]
                return result
            last_error = result.error

        return ScrapeResult(
            url=url,
            tier=start,
            success=False,
            status_code=None,
            content_preview="",
            error=last_error or "all tiers failed",
            escalated_from=escalated_from,
        )

    def _run_tier(self, url: str, tier: TierLevel, *, max_bytes: int) -> ScrapeResult:
        if tier == 1:
            return self._tier1(url, max_bytes)
        if tier == 2:
            return self._tier_browser(url, tier, headless=True, max_bytes=max_bytes)
        return self._tier_browser(url, tier, headless=False, max_bytes=max_bytes)

    def _tier1(self, url: str, max_bytes: int) -> ScrapeResult:
        proxies = None
        if self._proxy:
            proxies = self._proxy.get_endpoint().requests_proxies()
        try:
            r = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "NextbrowserHarness/1.2 (+https://nextbrowser.io)"},
                proxies=proxies,
            )
            blocked = r.status_code in (403, 429, 503) or "captcha" in r.text.lower()[:5000]
            if blocked:
                return ScrapeResult(
                    url, 1, False, r.status_code, "", error=f"blocked status={r.status_code}"
                )
            text = r.text[:max_bytes]
            return ScrapeResult(url, 1, True, r.status_code, text)
        except Exception as e:
            return ScrapeResult(url, 1, False, None, "", error=str(e))

    def _tier_browser(self, url: str, tier: TierLevel, *, headless: bool, max_bytes: int) -> ScrapeResult:
        layer = self._browser_layer()
        session = layer.ensure_profile("scrape_default")
        proxy_ep = self._proxy.get_endpoint() if self._proxy else None
        try:
            ctx = layer.launch_context(session, proxy=proxy_ep, headless=headless)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            blocked = page.locator("text=/captcha|access denied|blocked/i").count() > 0
            html = page.content()[:max_bytes]
            if blocked and len(html) < 500:
                return ScrapeResult(url, tier, False, None, "", error="browser blocked/captcha")
            return ScrapeResult(url, tier, True, 200, html)
        except Exception as e:
            return ScrapeResult(url, tier, False, None, "", error=str(e))
        finally:
            try:
                if hasattr(ctx, "_harness_mlx"):
                    ctx._harness_mlx.close()
                else:
                    ctx.close()
                    if hasattr(ctx, "_harness_playwright"):
                        ctx._harness_playwright.stop()
            except Exception:
                pass
