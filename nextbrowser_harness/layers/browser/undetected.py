from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.platform_hints import ensure_display_linux
from nextbrowser_harness.platform_paths import is_linux
from nextbrowser_harness.layers.browser.base import BrowserSession


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class UndetectedBrowserHolder:
    driver: object
    playwright: object
    browser: object

    def close(self) -> None:
        try:
            self.browser.close()
        except Exception:
            pass
        try:
            self.playwright.stop()  # type: ignore[union-attr]
        except Exception:
            pass
        try:
            self.driver.quit()  # type: ignore[union-attr]
        except Exception:
            pass


class UndetectedBrowserLayer:
    """Launch patched Chrome via undetected-chromedriver; attach Playwright over CDP."""

    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._holders: dict[str, UndetectedBrowserHolder] = {}

    @classmethod
    def from_config(cls, config: HarnessConfig) -> UndetectedBrowserLayer:
        return cls(Path(config.profiles_dir))

    def ensure_profile(self, profile_id: str) -> BrowserSession:
        path = self.profiles_dir / profile_id
        path.mkdir(parents=True, exist_ok=True)
        return BrowserSession(profile_id=profile_id, profile_path=str(path), headful=True)

    def launch_context(self, session: BrowserSession, *, proxy=None, headless: bool = True):
        try:
            import undetected_chromedriver as uc
        except ImportError as e:
            raise ImportError(
                "undetected-chromedriver required for native anti-detect browser. "
                "Install: pip install 'nextbrowser-harness[undetected]'"
            ) from e
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise ImportError(
                "Playwright required for browser tiers. Install: pip install 'nextbrowser-harness[playwright]' "
                "&& playwright install chromium"
            ) from e

        port = _free_port()
        options = uc.ChromeOptions()
        options.add_argument(f"--remote-debugging-port={port}")
        options.add_argument(f"--user-data-dir={session.profile_path}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        if headless:
            options.add_argument("--headless=new")

        proxy_dict = None
        if proxy:
            ep = proxy.playwright_proxy()
            if ep and ep.get("server"):
                server = ep["server"]
                if server.startswith("http://"):
                    server = server[7:]
                elif server.startswith("https://"):
                    server = server[8:]
                options.add_argument(f"--proxy-server={server}")
                if ep.get("username"):
                    proxy_dict = {"username": ep["username"], "password": ep.get("password") or ""}

        if is_linux() and headless and not ensure_display_linux().get("display_ok"):
            raise RuntimeError(
                "Headless Linux needs Xvfb for undetected Chrome: sudo apt install xvfb "
                "(or set DISPLAY / run under xvfb-run)"
            )

        driver = uc.Chrome(options=options, headless=headless, use_subprocess=True)
        cdp_url = f"http://127.0.0.1:{port}"

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp(cdp_url, timeout=60_000)
        except Exception as e:
            pw.stop()
            try:
                driver.quit()
            except Exception:
                pass
            raise RuntimeError(f"Playwright CDP connect failed ({cdp_url}): {e}") from e

        holder = UndetectedBrowserHolder(driver=driver, playwright=pw, browser=browser)
        self._holders[session.profile_id] = holder

        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        ctx._harness_uc = holder  # type: ignore[attr-defined]
        ctx._harness_cdp_url = cdp_url  # type: ignore[attr-defined]
        return ctx

    def stop(self, profile_id: str) -> None:
        holder = self._holders.pop(profile_id, None)
        if holder:
            holder.close()
