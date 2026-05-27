"""
Interpret live browser-use `state` output: URL, login likelihood, what the page is doing.

Single source of truth for "are we logged in?" heuristics — used by login, ui situation, skills.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


def extract_current_url_from_state(state_text: str) -> str:
    m = re.search(r"Current URL:\s*(\S+)", state_text or "", flags=re.I)
    return (m.group(1).strip() if m else "")


def count_indexed_elements(state_text: str) -> int:
    return len(re.findall(r"\[\d+\]", state_text or ""))


_STRENGTH_LOGGED_OUT = (
    r"\b(sign in|log in|login|create account|sign up|register|forgot password)\b"
)
_STRENGTH_LOGGED_IN = r"\b(log out|logout|sign out|signout)\b"
_WEAK_LOGGED_IN = r"\b(my account|your account|profile|settings|notifications|inbox)\b"


def infer_logged_in_from_state(state_text: str) -> bool | None:
    """
    Heuristic from browser-use `state` text.

    Returns True / False when evidence is reasonably strong; None if uncertain.
    """
    if not (state_text or "").strip():
        return None
    _explanation, verdict = infer_logged_in_with_reason(state_text)
    return verdict


def infer_logged_in_with_reason(state_text: str) -> tuple[str, bool | None]:
    """
    Return (human-readable reason, True|False|None).

    The reason is for agents and CLI JSON — never claim certainty when None.
    """
    raw = state_text or ""
    if not raw.strip():
        return "no snapshot (empty browser state)", None

    text = raw.lower()
    url = extract_current_url_from_state(state_text).lower()

    logoutish = bool(re.search(_STRENGTH_LOGGED_IN, text))
    login_formish = bool(re.search(_STRENGTH_LOGGED_OUT, text))
    weak_in = bool(re.search(_WEAK_LOGGED_IN, text))

    if login_formish and not logoutish:
        return (
            "Login / sign-up UI markers visible (likely logged out or on auth page).",
            False,
        )
    if logoutish:
        return ("Account chrome shows sign-out / log out (likely logged in).", True)
    if weak_in and not login_formish:
        return (
            "Account-style UI markers (profile, settings, inbox) without login gate.",
            True,
        )

    if "/login" in url or "/signin" in url or "/sign-in" in url or "/auth" in url:
        if logoutish:
            return ("On auth-ish URL but also see log out — ambiguous; treat as logged in.", True)
        return ("URL suggests auth/login path (likely logged out).", False)
    if any(k in url for k in ("/home", "/feed", "/dashboard", "/inbox")):
        if login_formish:
            return (
                "On app URL but login markers present — partly loaded or gated? uncertain.",
                None,
            )
        return ("On main app-style URL without login CTAs (possibly logged in).", True)

    return (
        "No strong login vs logged-out markers in visible state snapshot — uncertain.",
        None,
    )


@dataclass
class BrowserSituation:
    """Structured snapshot for agents."""

    connected: bool
    account_id: str = ""
    cdp_present: bool = False
    current_url: str = ""
    indexed_elements_approx: int = 0
    logged_in_likely: bool | None = None
    logged_in_registry: bool = False
    explanation: str = ""
    state_snippet: str = ""
    browser_use_ok: bool = False
    error: str | None = None
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_situation_from_state_text(
    state_text: str,
    *,
    account_id: str = "",
    registry_logged_in: bool = False,
    browser_use_exit_code: int = 0,
) -> BrowserSituation:
    snippet = (state_text or "")[-6000:]
    url = extract_current_url_from_state(state_text)
    n_idx = count_indexed_elements(state_text)
    explanation, likely = infer_logged_in_with_reason(state_text)

    hints: list[str] = []
    if registry_logged_in and likely is False:
        hints.append(
            "Registry says logged_in=true but live page looks logged out — session may have expired or wrong tab."
        )
    if registry_logged_in is False and likely is True:
        hints.append(
            "Live page suggests logged in but registry logged_in=false — run a successful login or mark account after verifying."
        )
    if likely is None:
        hints.append(
            "Open the logged-in homepage for this site and run `nextbrowser ui situation` again, or inspect `state_snippet` for [N] elements."
        )

    ok = browser_use_exit_code == 0 and bool(snippet.strip())
    return BrowserSituation(
        connected=True,
        account_id=account_id,
        cdp_present=True,
        current_url=url,
        indexed_elements_approx=n_idx,
        logged_in_likely=likely,
        logged_in_registry=registry_logged_in,
        explanation=explanation,
        state_snippet=snippet,
        browser_use_ok=ok,
        error=None if ok else "browser-use state failed or returned empty output",
        hints=hints,
    )
