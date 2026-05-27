"""Live MLX page check before agent-run (Playwright CDP, no browser-use)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nextbrowser_harness.integrations.multilogin.playwright_session import (
    capture_state_text,
    mlx_page,
)
from nextbrowser_harness.workflows.browser_intel import infer_logged_in_with_reason


@dataclass
class PreflightResult:
    logged_in_likely: bool | None
    explanation: str
    state_snippet: str
    browser_use_ok: bool
    opened_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "logged_in_likely": self.logged_in_likely,
            "explanation": self.explanation,
            "browser_use_ok": self.browser_use_ok,
            "engine": "mlx+playwright",
            "opened_url": self.opened_url,
            "state_snippet": self.state_snippet[-1500:] if self.state_snippet else "",
        }


def probe_login_state(
    cdp_url: str,
    account_id: str,
    *,
    open_url: str | None = None,
    timeout: int = 90,
    config=None,
) -> PreflightResult:
    from nextbrowser_harness.config import HarnessConfig

    cfg = config or HarnessConfig.load()
    _ = cdp_url
    _ = timeout
    try:
        with mlx_page(cfg, account_id=account_id) as page:
            if open_url:
                page.goto(open_url, wait_until="domcontentloaded", timeout=90_000)
            text = capture_state_text(page)
        explanation, likely = infer_logged_in_with_reason(text)
        return PreflightResult(
            logged_in_likely=likely,
            explanation=explanation,
            state_snippet=text,
            browser_use_ok=True,
            opened_url=open_url or "",
        )
    except Exception as e:
        return PreflightResult(
            logged_in_likely=None,
            explanation=str(e),
            state_snippet="",
            browser_use_ok=False,
        )
