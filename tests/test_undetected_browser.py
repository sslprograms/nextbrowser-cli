"""Tests for UndetectedBrowserLayer CDP attach."""

import sys
import types
from unittest.mock import MagicMock, patch

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.browser.undetected import UndetectedBrowserLayer


def test_undetected_connects_over_cdp(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path / "profiles"), driver="undetected")
    layer = UndetectedBrowserLayer.from_config(cfg)
    session = layer.ensure_profile("test")

    mock_driver = MagicMock()
    mock_browser = MagicMock()
    mock_browser.contexts = []
    mock_ctx = MagicMock(pages=[])
    mock_browser.new_context.return_value = mock_ctx
    mock_playwright = MagicMock()
    mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
    mock_pw_factory = MagicMock()
    mock_pw_factory.start.return_value = mock_playwright
    mock_options = MagicMock()

    mock_uc = types.ModuleType("undetected_chromedriver")
    mock_uc.ChromeOptions = MagicMock(return_value=mock_options)
    mock_uc.Chrome = MagicMock(return_value=mock_driver)

    with patch.dict(sys.modules, {"undetected_chromedriver": mock_uc}):
        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw_factory):
            ctx = layer.launch_context(session, headless=True)

    mock_playwright.chromium.connect_over_cdp.assert_called_once()
    cdp_url = mock_playwright.chromium.connect_over_cdp.call_args[0][0]
    assert cdp_url.startswith("http://127.0.0.1:")
    assert hasattr(ctx, "_harness_uc")
