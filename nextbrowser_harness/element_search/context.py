"""Element search mode resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from nextbrowser_harness.config import HarnessConfig

ElementSearchMode = Literal["playwright", "indexed"]


@dataclass
class ElementSearchContext:
    mode: ElementSearchMode
    cdp_url: str | None = None  # unused for indexed; kept for API compat


def resolve_element_search_mode(
    config: HarnessConfig,
    *,
    override: str | None = None,
) -> ElementSearchMode:
    """
    ``indexed`` — numbered interactive elements for agents (state / click:N / type:N|value).
    ``playwright`` — CSS locators only.
    """
    raw = (override or os.getenv("NEXTBROWSER_ELEMENT_SEARCH") or "").strip().lower()
    if not raw:
        raw = (getattr(config, "element_search", "") or "").strip().lower()
    if not raw:
        # Default: indexed map for agents (no browser-use package required)
        raw = "indexed"
    if raw in ("indexed", "index", "agent", "ai", "browser_use", "browser-use", "bu"):
        return "indexed"
    return "playwright"
