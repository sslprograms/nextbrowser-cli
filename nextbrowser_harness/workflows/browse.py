"""
Interactive browser session — delegates to exec_site (single navigation path for agents).
"""

from __future__ import annotations

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.workflows.browser_result import BrowseResult
from nextbrowser_harness.workflows.exec import exec_site

__all__ = ["BrowseResult", "browse_site"]


def browse_site(
    config: HarnessConfig,
    url: str,
    *,
    tier: int | None = None,
    profile_id: str | None = None,
    headless: bool | None = None,
    screenshot: str | None = None,
    actions: list[str] | None = None,
    steps_file: str | None = None,
    js: str | None = None,
    js_file: str | None = None,
    keep_open: bool = False,
) -> BrowseResult:
    """Open URL and run actions — same engine as `nextbrowser exec`."""
    default_actions = actions or ["goto", "wait_load", "title", "scroll", "reddit_feed_check", "final_url"]
    result = exec_site(
        config,
        url,
        tier=tier,
        profile_id=profile_id,
        headless=headless,
        screenshot=screenshot,
        actions=default_actions,
        steps_file=steps_file,
        js=js,
        js_file=js_file,
        keep_open=keep_open,
    )
    return BrowseResult(**result.to_dict())
