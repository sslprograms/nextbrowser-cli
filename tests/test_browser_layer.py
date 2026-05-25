"""Browser layer routing."""

from unittest.mock import patch

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.browser.antidetect import browser_layer_for
from nextbrowser_harness.layers.browser.native import NativeBrowserLayer


def test_browser_layer_native_playwright(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path), driver="playwright")
    layer = browser_layer_for(cfg)
    assert isinstance(layer, NativeBrowserLayer)


def test_browser_layer_native_undetected(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path), driver="undetected")
    with patch(
        "nextbrowser_harness.layers.browser.undetected.UndetectedBrowserLayer.from_config"
    ) as mock_uc:
        mock_uc.return_value = object()
        browser_layer_for(cfg)
        mock_uc.assert_called_once_with(cfg)
