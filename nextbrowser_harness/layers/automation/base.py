from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from nextbrowser_harness.config import HarnessConfig


@dataclass
class AutomationResult:
    success: bool
    output: str
    error: str | None = None


class AutomationLayer(Protocol):
    def run_task(self, task: str, *, url: str | None = None, profile_id: str = "default") -> AutomationResult: ...

    @classmethod
    def from_config(cls, config: HarnessConfig) -> AutomationLayer: ...
