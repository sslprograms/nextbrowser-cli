"""Shared result type for browse/exec workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BrowseResult:
    url: str
    browser: str
    tier: int
    success: bool
    title: str | None = None
    final_url: str | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    screenshot_path: str | None = None
    tier_source: str | None = None
    multilogin_recommendation: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return asdict(self)
