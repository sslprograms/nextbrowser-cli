from pathlib import Path

from nextbrowser_harness.tiers.resolver import TierResolver


def test_database_lookup_reddit(tmp_path):
    r = TierResolver(tmp_path / "cache.yaml")
    rec = r.recommended_tier("https://www.reddit.com/r/python")
    assert rec.tier == 3
    assert rec.source == "database"


def test_default_tier_unknown_domain(tmp_path):
    r = TierResolver(tmp_path / "cache.yaml")
    rec = r.recommended_tier("https://unknown-test-domain-xyz.example")
    assert rec.tier == 1
    assert rec.source == "default"


def test_cache_after_success(tmp_path):
    r = TierResolver(tmp_path / "cache.yaml")
    r.remember_success("foo.example", 2)
    rec = r.recommended_tier("https://foo.example/page")
    assert rec.tier == 2
    assert rec.source == "cache"


def test_escalation_order():
    r = TierResolver(Path("/tmp/x.yaml"))
    assert r.escalation_order(2) == [2, 3]
