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
    r"\b(sign in|log in|login|create account|sign up|register|forgot password|"
    r"reset password|continue with google|continue with apple)\b"
)
_STRENGTH_LOGGED_IN = r"\b(log out|logout|sign out|signout|sign-out)\b"
_WEAK_LOGGED_IN = (
    r"\b(my account|your account|profile|settings|notifications|inbox|"
    r"user menu|avatar|compose|create post|new post|dashboard|account settings)\b"
)
_AUTH_URL_MARKERS = (
    "/login",
    "/log-in",
    "/signin",
    "/sign-in",
    "/signup",
    "/sign-up",
    "/register",
    "/auth/",
    "/oauth",
    "/session/new",
    "/accounts/login",
)
_APP_URL_MARKERS = ("/home", "/feed", "/dashboard", "/inbox", "/app/", "/portal")
_PROFILE_URL_MARKERS = ("/user/", "/users/", "/profile/", "/account/", "/me/", "/@")


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

    # Common auth gate: both "log in" and "sign up" visible, no sign-out
    if (
        re.search(r"\b(log in|sign in)\b", text)
        and re.search(r"\b(sign up|create account|register)\b", text)
        and not logoutish
    ):
        return (
            "Auth gate visible (Log in + Sign up) with no sign-out — not logged in.",
            False,
        )

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

    if any(m in url for m in _AUTH_URL_MARKERS):
        if logoutish:
            return ("On auth URL but sign-out also visible — treating as logged in.", True)
        return ("URL is an auth/login path (likely logged out).", False)

    if any(m in url for m in _PROFILE_URL_MARKERS) and not login_formish:
        return ("On profile/account URL without login gate (likely logged in).", True)

    if any(k in url for k in _APP_URL_MARKERS):
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


def normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def text_visible_in_state(state_text: str, needle: str, *, min_len: int = 8) -> bool:
    """Case-insensitive substring check — proves submitted text appears on the live page."""
    n = normalize_for_match(needle)
    if len(n) < min_len:
        return False
    hay = normalize_for_match(state_text)
    return n in hay


def agent_gates(
    *,
    logged_in_likely: bool | None,
    browser_use_ok: bool,
    site: str = "",
) -> dict[str, Any]:
    """
    Machine-readable rules for external agents — if these are false, do NOT claim success.
    """
    logged_ok = logged_in_likely is True and browser_use_ok
    login_cmd = (
        f"nextbrowser login <account> --url {site}"
        if site
        else "nextbrowser login <account> --url <target-site>"
    )
    return {
        "logged_in_verified": logged_ok,
        "safe_to_claim_logged_in": logged_ok,
        "safe_to_claim_content_posted": False,  # only True after ui verify --text exits 0
        "safe_to_claim_comment_posted": False,  # alias; same as content_posted
        "safe_to_claim_task_complete": logged_ok,
        "forbidden_without_proof": [
            "logged in",
            "login complete",
            "posted",
            "published",
            "submitted successfully",
            "comment posted",
            "verified",
            "task complete",
        ],
        "required_commands": [
            "nextbrowser ui require-login  # exit 0 before any authenticated action",
            "nextbrowser ui situation  # read agent_gates; exit 1 if not logged in",
            'nextbrowser ui verify --text "<exact submitted text>"  # exit 0 = on-page proof',
        ],
        "if_logged_in_verified_is_false": (
            f"STOP. Run `{login_cmd}` with real credentials or finish auth in the MLX window, "
            "then `nextbrowser ui require-login`. Do not claim login or that content was posted."
        ),
    }


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
    agent_gates: dict[str, Any] = field(default_factory=dict)

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
    gates = agent_gates(logged_in_likely=likely, browser_use_ok=ok, site=url)
    if not gates["logged_in_verified"]:
        hints.append(gates["if_logged_in_verified_is_false"])
    hints.append(
        "After any submit (post, comment, form, message), run: "
        'nextbrowser ui verify --text "<exact text you submitted>" '
        "(exit 0 = visible on page; exit 1 = action did NOT succeed — do not claim success)."
    )

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
        agent_gates=gates,
    )
