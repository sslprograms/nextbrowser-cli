from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.recommend import multilogin_recommendation


def test_recommends_mlx_for_reddit_native_browser():
    cfg = HarnessConfig(browser="native", use_case="scrape")
    hint = multilogin_recommendation(cfg, "https://www.reddit.com")
    assert hint is not None
    assert hint["recommend_multilogin"] is True
    assert hint["tier_recommended"] == 3


def test_no_recommend_when_already_multilogin():
    cfg = HarnessConfig(browser="multilogin")
    assert multilogin_recommendation(cfg, "https://www.reddit.com") is None


def test_no_recommend_tier1_simple_site(tmp_path):
    cfg = HarnessConfig(browser="native", tier_cache_path=str(tmp_path / "empty_cache.yaml"))
    hint = multilogin_recommendation(cfg, "https://example.com", cache_path=cfg.tier_cache_path)
    assert hint is None
