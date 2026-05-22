from __future__ import annotations

from pathlib import Path

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.browser.base import BrowserSession


class NativeBrowserLayer:
    """Bundled Chromium via Playwright — default MVP browser."""

    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_config(cls, config: HarnessConfig) -> NativeBrowserLayer:
        return cls(Path(config.profiles_dir))

    def ensure_profile(self, profile_id: str) -> BrowserSession:
        path = self.profiles_dir / profile_id
        path.mkdir(parents=True, exist_ok=True)
        return BrowserSession(profile_id=profile_id, profile_path=str(path), headful=False)

    def launch_context(self, session: BrowserSession, *, proxy=None, headless: bool = True):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise ImportError(
                "Playwright required for browser tiers. Install: pip install 'nextbrowser-harness[playwright]' "
                "&& playwright install chromium"
            ) from e

        pw = sync_playwright().start()
        launch_args = {"headless": headless, "args": ["--disable-blink-features=AutomationControlled"]}
        browser = pw.chromium.launch_persistent_context(
            session.profile_path,
            channel=None,
            proxy=proxy.playwright_proxy() if proxy else None,
            **launch_args,
        )
        browser._harness_playwright = pw  # type: ignore[attr-defined]
        return browser
