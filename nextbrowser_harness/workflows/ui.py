"""
Convenience UI commands for agents — thin wrappers over browser-use that reuse the
saved CDP session from `nextbrowser login` / `browser-use connect`.

Why this exists: agents previously fumbled `browser-use --cdp-url ...` for every step.
Now they run `nextbrowser ui state`, `nextbrowser ui click 5`, etc. The browser
profile stays open between calls because we never stop the MLX session.

`ui close` is the canonical end of a task — it disconnects browser-use and stops
the MLX profile cleanly.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import asdict, dataclass
from typing import Any

from nextbrowser_harness.accounts.registry import AccountRegistry
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.browser_use.bridge import (
    browser_use_bin,
    disconnect_account,
    load_session,
)
from nextbrowser_harness.workflows.browser_intel import (
    agent_gates,
    build_situation_from_state_text,
    text_visible_in_state,
)
from nextbrowser_harness.workflows.browser_use_exec import bu_call, bu_chain, capture_state


@dataclass
class UIResult:
    success: bool
    command: str
    args: list[str]
    stdout: str = ""
    stderr: str = ""
    cdp_url: str = ""
    account_id: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_NEEDS_INDEX = {"click", "input", "type", "hover", "dblclick", "rightclick", "select", "upload", "get"}
_ALIASES = {
    "type": "input",     # ergonomic — `ui type 5 "hello"` runs `input 5 hello`
    "fill": "input",
    "submit": "click",
}


def _resolve_cmd(name: str) -> str:
    return _ALIASES.get(name, name)


def run(
    config: HarnessConfig,
    command: str,
    *,
    args: list[str] | None = None,
    timeout: int = 60,
) -> UIResult:
    """Pass-through to browser-use using the saved CDP from connect/login."""
    sess = load_session()
    if not sess or not sess.get("cdp_url"):
        return UIResult(
            success=False,
            command=command,
            args=args or [],
            error=(
                "No browser session. Start with: "
                "nextbrowser login <account> --url <url>  (or `browser-use connect`)"
            ),
        )
    cdp = sess["cdp_url"]
    bin_path = browser_use_bin()
    if not bin_path:
        return UIResult(
            success=False,
            command=command,
            args=args or [],
            cdp_url=cdp,
            account_id=sess.get("account_id", ""),
            error="browser-use CLI not installed (https://browser-use.com/cli/install.sh).",
        )
    cmd = _resolve_cmd(command)
    cmd_args = list(args or [])
    proc = bu_call(
        bin_path,
        cdp,
        [cmd, *cmd_args],
        account_id=sess.get("account_id"),
        timeout=timeout,
    )
    return UIResult(
        success=proc.returncode == 0,
        command=command,
        args=cmd_args,
        stdout=(proc.stdout or "")[-8000:],
        stderr=(proc.stderr or "")[-2000:],
        cdp_url=cdp,
        account_id=sess.get("account_id", ""),
        error=None if proc.returncode == 0 else f"exit {proc.returncode}",
    )


def situation(
    config: HarnessConfig,
    *,
    timeout: int = 60,
    strict: bool = True,
) -> dict[str, Any]:
    """
    Snapshot what the MLX-attached browser is actually showing: URL, login estimate,
    match vs accounts.json `logged_in`, and an element map snippet from browser-use state.
    """
    sess = load_session()
    if not sess or not sess.get("cdp_url"):
        return {
            "connected": False,
            "account_id": "",
            "current_url": "",
            "logged_in_likely": None,
            "logged_in_registry": False,
            "explanation": "No active CDP session.",
            "error": (
                "No browser session. Run `nextbrowser login <account> --url <url>` "
                "or `nextbrowser browser-use connect --account <name>`."
            ),
            "hints": [
                "After connect/login, Multilogin tab must stay open.",
            ],
        }
    aid = sess.get("account_id", "") or ""
    reg = AccountRegistry(config).get(aid)
    logged_r = bool(reg.logged_in) if reg else False

    bin_path = browser_use_bin()
    if not bin_path:
        return {
            "connected": True,
            "account_id": aid,
            "cdp_present": True,
            "logged_in_registry": logged_r,
            "explanation": "Cannot read live page.",
            "error": (
                "browser-use CLI missing. Install from https://browser-use.com/cli/install.sh"
            ),
        }

    cdp = sess["cdp_url"]
    text, rc, stderr_tail = capture_state(
        bin_path, cdp, account_id=aid, timeout=timeout
    )
    snap = build_situation_from_state_text(
        text,
        account_id=aid,
        registry_logged_in=logged_r,
        browser_use_exit_code=rc,
    )
    out = snap.to_dict()
    if rc != 0 and stderr_tail:
        out["stderr_tail"] = stderr_tail
    out["mlx_profile_id"] = sess.get("mlx_profile_id", "")
    out["strict"] = strict
    gates = out.get("agent_gates") or {}
    out["cli_should_exit_nonzero"] = bool(
        strict and not gates.get("logged_in_verified")
    )
    return out


def require_login(config: HarnessConfig, *, timeout: int = 60) -> dict[str, Any]:
    """Fail-closed gate: exit 0 only when live page proves logged in."""
    out = situation(config, timeout=timeout, strict=True)
    gates = out.get("agent_gates") or agent_gates(
        logged_in_likely=out.get("logged_in_likely"),
        browser_use_ok=out.get("browser_use_ok", False),
        site=out.get("current_url", ""),
    )
    verified = gates.get("logged_in_verified", False)
    out["require_login_ok"] = verified
    if not verified:
        out["error"] = out.get("error") or (
            "NOT LOGGED IN — do not post comments or tell the user login succeeded. "
            f"{gates.get('if_logged_in_verified_is_false', '')}"
        )
    return out


def verify_text(
    config: HarnessConfig,
    text: str,
    *,
    timeout: int = 60,
    min_len: int = 8,
) -> dict[str, Any]:
    """
    Proof that submitted text appears in the live browser-use state snapshot.
    Works for any site (posts, comments, forms, messages). Exit 0 = safe to claim success.
    """
    sess = load_session()
    if not sess or not sess.get("cdp_url"):
        return {
            "verified": False,
            "error": "No browser session. Run `nextbrowser login` first.",
        }
    aid = sess.get("account_id", "") or ""
    bin_path = browser_use_bin()
    if not bin_path:
        return {"verified": False, "error": "browser-use CLI not installed."}

    state_text, rc, stderr_tail = capture_state(
        bin_path, sess["cdp_url"], account_id=aid, timeout=timeout
    )
    needle = (text or "").strip()
    if len(needle) < min_len:
        return {
            "verified": False,
            "error": f"Need at least {min_len} characters of text to verify.",
            "text_needle": needle,
        }
    found = text_visible_in_state(state_text, needle, min_len=min_len)
    gates = agent_gates(
        logged_in_likely=None,
        browser_use_ok=rc == 0,
        site="",
    )
    return {
        "verified": found,
        "text_needle": needle[:120],
        "account_id": aid,
        "browser_use_ok": rc == 0,
        "agent_gates": {
            **gates,
            "safe_to_claim_content_posted": found,
            "safe_to_claim_comment_posted": found,
        },
        "stderr_tail": stderr_tail if rc != 0 else "",
        "state_snippet": state_text[-1500:] if not found else "",
        "error": None
        if found
        else (
            "Submitted text NOT found on page — do NOT tell the user the action succeeded. "
            "Re-run ui situation, complete the action again, then verify."
        ),
    }


def scroll(
    config: HarnessConfig,
    direction: str = "down",
    pages: float = 1.0,
    *,
    timeout: int = 60,
) -> UIResult:
    """
    Scroll the page via browser-use (feed posts, lazy-loaded comments).

    Tries common CLI shapes; use `ui run scroll ...` if your browser-use version differs.
    """
    pages_s = str(pages)
    for args in (
        ["scroll", direction, pages_s],
        ["scroll", f"{direction}", "--num-pages", pages_s],
        ["scroll", "--direction", direction, "--num-pages", pages_s],
    ):
        res = run(config, "scroll", args=args, timeout=timeout)
        if res.success:
            return res
    return res


def close(config: HarnessConfig) -> dict[str, Any]:
    """Disconnect browser-use and stop the MLX profile — end of task."""
    sess = load_session() or {}
    account = sess.get("account_id", "")
    if not account:
        return {"success": True, "note": "no active session"}
    return disconnect_account(config, account)


def chain(
    config: HarnessConfig,
    steps: list[str],
    *,
    timeout: int = 300,
) -> UIResult:
    """Run multiple steps as ONE shell pipe so browser-use daemon never restarts."""
    sess = load_session()
    if not sess or not sess.get("cdp_url"):
        return UIResult(
            success=False,
            command="chain",
            args=steps,
            error="No browser session. Start with `nextbrowser login`.",
        )
    bin_path = browser_use_bin()
    if not bin_path:
        return UIResult(
            success=False,
            command="chain",
            args=steps,
            error="browser-use CLI not installed.",
        )
    cdp = sess["cdp_url"]
    posix = subprocess.os.name != "nt"
    parsed: list[list[str]] = []
    for raw in steps:
        parsed.append(shlex.split(raw, posix=posix))
    proc = bu_chain(
        bin_path,
        cdp,
        parsed,
        account_id=sess.get("account_id"),
        timeout=timeout,
    )
    return UIResult(
        success=proc.returncode == 0,
        command="chain",
        args=steps,
        stdout=(proc.stdout or "")[-8000:],
        stderr=(proc.stderr or "")[-2000:],
        cdp_url=cdp,
        account_id=sess.get("account_id", ""),
    )
