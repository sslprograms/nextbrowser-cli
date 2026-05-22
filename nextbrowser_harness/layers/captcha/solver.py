from __future__ import annotations

from nextbrowser_harness.config import HarnessConfig


class CaptchaSolver:
    """Optional CAPTCHA — user supplies token; provider hooks are stubs in MVP."""

    def __init__(self, enabled: bool, provider: str | None, token: str | None):
        self.enabled = enabled
        self.provider = provider
        self.token = token

    @classmethod
    def from_config(cls, config: HarnessConfig) -> CaptchaSolver:
        return cls(config.captcha_enabled, config.captcha_provider, config.captcha_token)

    def solve(self, site_key: str, page_url: str) -> str | None:
        if not self.enabled or not self.token:
            return None
        # MVP: integrate 2Captcha/CapMonster HTTP API in a follow-up release
        raise NotImplementedError(
            f"CAPTCHA solving ({self.provider}) is configured but not wired in MVP. "
            "Disable captcha or implement provider API."
        )
