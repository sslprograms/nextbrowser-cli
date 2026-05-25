from pathlib import Path

from nextbrowser_harness.config import HarnessConfig


def test_config_roundtrip(tmp_path):
    cfg = HarnessConfig(use_case="accounts", browser="gologin", proxy="custom", driver="playwright")
    path = tmp_path / "cfg.yaml"
    cfg.save(path)
    loaded = HarnessConfig.load(path)
    assert loaded.use_case == "accounts"
    assert loaded.browser == "gologin"
    assert loaded.driver == "playwright"
    assert loaded.proxy == "custom"


def test_config_defaults():
    cfg = HarnessConfig()
    assert cfg.proxy == "none"
    assert cfg.driver == "undetected"
