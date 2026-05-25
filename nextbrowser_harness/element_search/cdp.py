"""Resolve CDP WebSocket/HTTP URL from a Playwright browser context."""

from __future__ import annotations


def get_cdp_url_from_context(ctx) -> str | None:
    """CDP endpoint set by MLX / undetected layers, or None."""
    url = getattr(ctx, "_harness_cdp_url", None)
    if url:
        return str(url).strip() or None
    return None
