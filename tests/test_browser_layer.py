"""Browser layer routing."""

import sys
from unittest.mock import MagicMock, patch

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.browser.antidetect import browser_layer_for
from nextbrowser_harness.layers.browser.native import NativeBrowserLayer


def test_browser_layer_native_playwright(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path), driver="playwright")
    layer = browser_layer_for(cfg)
    assert isinstance(layer, NativeBrowserLayer)


def test_browser_layer_native_undetected(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path), driver="undetected")
    with (
        patch.dict(sys.modules, {"undetected_chromedriver": MagicMock()}),
        patch(
            "nextbrowser_harness.layers.browser.undetected.UndetectedBrowserLayer.from_config"
        ) as mock_uc,
    ):
        mock_uc.return_value = object()
        browser_layer_for(cfg)
        mock_uc.assert_called_once_with(cfg)


def test_browser_layer_native_undetected_fallback(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path), driver="undetected")
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "undetected_chromedriver":
            raise ImportError("no uc")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", fake_import):
        layer = browser_layer_for(cfg)
    assert isinstance(layer, NativeBrowserLayer)
