"""
Playwright over Multilogin CDP — no browser-use CLI or cloud API.

Requires an explicit account name. Does not read ~/.nextbrowser session files
unless the caller passes use_saved_session=True.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.account_cli import (
    AccountRequiredError,
    resolve_account_id,
)
from nextbrowser_harness.integrations.multilogin.browser import MultiloginBrowserLayer


@contextmanager
def mlx_page(
    config: HarnessConfig,
    *,
    account_id: str | None = None,
    use_saved_session: bool = False,
    headless: bool = False,
) -> Iterator[Any]:
    """
    Yield a Playwright Page attached to a **running** MLX profile via CDP.

    Requires ``connect --account <name>`` first (does not auto-start the profile).
    """
    aid = resolve_account_id(account_id, use_saved_session=use_saved_session)

    layer = MultiloginBrowserLayer.from_config(config)
    session = layer.ensure_profile(aid)
    ctx = layer.launch_context(session, headless=headless, start_if_stopped=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        yield page
    finally:
        layer.detach(aid)


def capture_state_text(page) -> str:
    """Indexed element map + URL (legacy helper)."""
    from nextbrowser_harness.element_search.indexed import IndexedElementSearch

    url = page.url or ""
    driver = IndexedElementSearch(page)
    body = driver.refresh_state()
    return f"Current URL: {url}\n\n{body}"
