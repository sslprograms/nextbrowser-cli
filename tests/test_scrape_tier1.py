from pathlib import Path

import pytest

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.tiers.resolver import TierResolver
from nextbrowser_harness.workflows.scraping import ScrapingWorkflow


@pytest.mark.integration
def test_tier1_httpbin():
    cfg = HarnessConfig(proxy="custom", custom_proxies=[])  # no proxy
    # Force tier 1 only by overriding escalation - scrape with force_tier=1
    r = ScrapingWorkflow(cfg, TierResolver(Path("/tmp/tcache.yaml"))).scrape(
        "https://httpbin.org/get", force_tier=1
    )
    assert r.success
    assert r.tier == 1
    assert "httpbin" in r.content_preview.lower() or "origin" in r.content_preview.lower()
