from __future__ import annotations

from nextbrowser_harness.config import BrowserChoice, HarnessConfig
from nextbrowser_harness.layers.browser.native import NativeBrowserLayer

INSTALL_GUIDES = {
    "multilogin": "https://documenter.getpostman.com/view/28533318/2s946h9Cv9 — MLX agent + folder/profile UUIDs",
    "gologin": "https://gologin.com — install GoLogin app, export profile IDs into harness config.",
    "octo": "https://octobrowser.net — install Octo Browser, map OCTO_PROFILE_ID per account.",
}


def browser_layer_for(config: HarnessConfig):
    """Pick browser layer from harness config."""
    if config.browser == "native":
        if config.driver == "playwright":
            return NativeBrowserLayer.from_config(config)
        from nextbrowser_harness.layers.browser.undetected import UndetectedBrowserLayer

        return UndetectedBrowserLayer.from_config(config)
    if config.browser == "multilogin":
        from nextbrowser_harness.integrations.multilogin.browser import MultiloginBrowserLayer

        return MultiloginBrowserLayer.from_config(config)
    return AntiDetectBrowserLayer.from_config(config)


class AntiDetectBrowserLayer:
    """Stub for GoLogin / Octo — Multilogin uses integrations.multilogin."""

    def __init__(self, provider: BrowserChoice, profiles_dir: str):
        self.provider = provider
        self._native_fallback = NativeBrowserLayer.from_config(
            HarnessConfig(profiles_dir=profiles_dir)
        )

    @classmethod
    def from_config(cls, config: HarnessConfig) -> AntiDetectBrowserLayer:
        if config.browser == "native":
            raise ValueError("Use NativeBrowserLayer for native browser")
        if config.browser == "multilogin":
            raise ValueError("Use MultiloginBrowserLayer for multilogin")
        return cls(config.browser, config.profiles_dir)

    def ensure_profile(self, profile_id: str):
        import os

        env_key = f"{self.provider.upper()}_PROFILE_{profile_id.upper()}"
        if not os.getenv(env_key):
            print(f"Note ({self.provider}): set {env_key} or see: {INSTALL_GUIDES.get(self.provider)}")
        return self._native_fallback.ensure_profile(f"{self.provider}_{profile_id}")

    def launch_context(self, session, *, proxy=None, headless: bool = False):
        return self._native_fallback.launch_context(session, proxy=proxy, headless=headless)
