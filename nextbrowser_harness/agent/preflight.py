"""Live CDP preflight before agent-run (login state + optional navigation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nextbrowser_harness.integrations.browser_use.bridge import browser_use_bin
from nextbrowser_harness.workflows.browser_intel import infer_logged_in_with_reason
from nextbrowser_harness.workflows.browser_use_exec import bu_call, capture_state


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
            "opened_url": self.opened_url,
            "state_snippet": self.state_snippet[-1500:] if self.state_snippet else "",
        }


def probe_login_state(
    cdp_url: str,
    account_id: str,
    *,
    open_url: str | None = None,
    timeout: int = 90,
) -> PreflightResult:
    """
    Open URL (optional) and read browser-use state — same signal as ui situation.
    """
    bin_path = browser_use_bin()
    if not bin_path:
        return PreflightResult(
            logged_in_likely=None,
            explanation="browser-use CLI not installed — cannot probe live login state",
            state_snippet="",
            browser_use_ok=False,
        )

    opened = ""
    if open_url:
        proc = bu_call(
            bin_path,
            cdp_url,
            ["open", open_url],
            account_id=account_id,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return PreflightResult(
                logged_in_likely=None,
                explanation=f"Failed to open {open_url}",
                state_snippet=(proc.stderr or proc.stdout or "")[-2000:],
                browser_use_ok=False,
                opened_url=open_url,
            )
        opened = open_url

    text, rc, _ = capture_state(bin_path, cdp_url, account_id=account_id, timeout=timeout)
    explanation, likely = infer_logged_in_with_reason(text)
    return PreflightResult(
        logged_in_likely=likely,
        explanation=explanation,
        state_snippet=text,
        browser_use_ok=rc == 0 and bool(text.strip()),
        opened_url=opened,
    )
