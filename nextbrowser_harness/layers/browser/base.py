from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from nextbrowser_harness.config import HarnessConfig


@dataclass
class BrowserSession:
    profile_id: str
    profile_path: str
    headful: bool


class BrowserLayer(Protocol):
    def ensure_profile(self, profile_id: str) -> BrowserSession: ...

    def launch_context(self, session: BrowserSession, *, proxy: Any = None, headless: bool = True): ...

    @classmethod
    def from_config(cls, config: HarnessConfig) -> BrowserLayer: ...
