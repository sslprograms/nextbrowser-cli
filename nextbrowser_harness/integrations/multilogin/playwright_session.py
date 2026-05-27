"""
Playwright over Multilogin CDP — no browser-use CLI or cloud API.

Each CLI command reconnects to the MLX profile's CDP port (profile stays open).
Agents use ``nextbrowser ui state / click / type`` like browser-use UX, MLX-only.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.browser import MultiloginBrowserLayer


def load_mlx_session() -> dict[str, Any] | None:
    """CDP session metadata (account, mlx profile, cdp_url)."""
    from nextbrowser_harness.integrations.browser_use.bridge import load_session

    return load_session()


def save_mlx_session(data: dict[str, Any]) -> None:
    from nextbrowser_harness.integrations.browser_use.bridge import save_session

    save_session(data)


@contextmanager
def mlx_page(
    config: HarnessConfig,
    *,
    account_id: str | None = None,
    headless: bool = False,
) -> Iterator[Any]:
    """
    Yield a Playwright Page attached to the MLX profile via CDP.
    Detaches Playwright on exit; MLX browser keeps running (cookies persist).
    """
    sess = load_mlx_session()
    aid = account_id or (sess or {}).get("account_id") or ""
    if not aid:
        raise RuntimeError(
            "No MLX session. Run: nextbrowser connect --account <name> "
            "or nextbrowser login <account> --url <url>"
        )

    layer = MultiloginBrowserLayer.from_config(config)
    session = layer.ensure_profile(aid)
    ctx = layer.launch_context(session, headless=headless)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        yield page
    finally:
        layer.detach(aid)


def capture_state_text(page) -> str:
    """Indexed element map + URL (agent-readable, same role as browser-use state)."""
    from nextbrowser_harness.element_search.indexed import IndexedElementSearch

    url = page.url or ""
    driver = IndexedElementSearch(page)
    body = driver.refresh_state()
    return f"Current URL: {url}\n\n{body}"
