from __future__ import annotations

import os
from dataclasses import dataclass

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.client import MultiloginXClient, MultiloginXError
from nextbrowser_harness.layers.browser.base import BrowserSession


@dataclass
class MultiloginBrowserSession(BrowserSession):
    mlx_profile_id: str = ""
    mlx_folder_id: str = ""


class MultiloginBrowserLayer:
    """
    Launch real Multilogin X profiles via Launcher API, connect Playwright over CDP.
    """

    def __init__(self, config: HarnessConfig, client: MultiloginXClient | None = None):
        self.config = config
        self.client = client or MultiloginXClient()
        self._mlx = config.multilogin or {}
        self._running: dict[str, StartedProfileHolder] = {}

    @classmethod
    def from_config(cls, config: HarnessConfig) -> MultiloginBrowserLayer:
        return cls(config)

    def default_folder_id(self) -> str:
        return (
            self._mlx.get("folder_id")
            or os.getenv("MULTILOGIN_FOLDER_ID", "")
        )

    def resolve_profile_id(self, account_key: str) -> tuple[str, str]:
        """
        Map harness account key -> (folder_id, profile_uuid).
        Env: MULTILOGIN_PROFILE_<KEY>, config multilogin.profiles dict, or MULTILOGIN_PROFILE_ID default.
        """
        profiles = self._mlx.get("profiles") or {}
        folder_id = self.default_folder_id()
        env_key = f"MULTILOGIN_PROFILE_{account_key.upper().replace('-', '_')}"
        profile_id = (
            profiles.get(account_key)
            or os.getenv(env_key)
            or self._mlx.get("default_profile_id")
            or os.getenv("MULTILOGIN_PROFILE_ID", "")
        )
        if not folder_id or not profile_id:
            raise MultiloginXError(
                f"Set MULTILOGIN_FOLDER_ID and profile id ({env_key} or multilogin.profiles in config). "
                "List folders: nextbrowser multilogin folders"
            )
        return folder_id, profile_id

    def ensure_profile(self, profile_id: str) -> MultiloginBrowserSession:
        folder_id, mlx_profile_id = self.resolve_profile_id(profile_id)
        return MultiloginBrowserSession(
            profile_id=profile_id,
            profile_path=f"multilogin:{mlx_profile_id}",
            headful=True,
            mlx_profile_id=mlx_profile_id,
            mlx_folder_id=folder_id,
        )

    def launch_context(self, session: BrowserSession, *, proxy=None, headless: bool = False):
        if not isinstance(session, MultiloginBrowserSession):
            session = self.ensure_profile(session.profile_id)

        started = self.client.start_profile(
            session.mlx_folder_id,
            session.mlx_profile_id,
            automation_type="playwright",
            headless=headless,
        )
        cdp = started.cdp_url
        if not cdp:
            raise MultiloginXError(
                f"No automation port returned for profile {session.mlx_profile_id}. "
                f"Is the Multilogin X launcher running? Response: {started.raw}"
            )

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise ImportError(
                "pip install 'nextbrowser-harness[playwright]' && playwright install chromium"
            ) from e

        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp(cdp, timeout=60_000)
        except Exception as e:
            pw.stop()
            self.client.stop_profile(session.mlx_profile_id)
            raise MultiloginXError(f"Playwright CDP connect failed ({cdp}): {e}") from e

        holder = StartedProfileHolder(
            playwright=pw,
            browser=browser,
            mlx_profile_id=session.mlx_profile_id,
            client=self.client,
        )
        self._running[session.profile_id] = holder

        # Return first context as primary; attach cleanup metadata
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        ctx._harness_mlx = holder  # type: ignore[attr-defined]
        return ctx

    def stop(self, profile_id: str) -> None:
        holder = self._running.pop(profile_id, None)
        if holder:
            holder.close()


@dataclass
class StartedProfileHolder:
    playwright: object
    browser: object
    mlx_profile_id: str
    client: MultiloginXClient

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
            self.client.stop_profile(self.mlx_profile_id)
        except Exception:
            pass
