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
from nextbrowser_harness.workflows.browser_intel import build_situation_from_state_text


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
    proc = subprocess.run(
        [bin_path, "--cdp-url", cdp, cmd, *cmd_args],
        capture_output=True,
        text=True,
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


def situation(config: HarnessConfig, *, timeout: int = 60) -> dict[str, Any]:
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
    proc = subprocess.run(
        [bin_path, "--cdp-url", cdp, "state"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    text = proc.stdout or proc.stderr or ""
    snap = build_situation_from_state_text(
        text,
        account_id=aid,
        registry_logged_in=logged_r,
        browser_use_exit_code=proc.returncode,
    )
    out = snap.to_dict()
    if proc.returncode != 0:
        tail = (proc.stderr or "")[-1200:] or ""
        out["stderr_tail"] = tail
    out["mlx_profile_id"] = sess.get("mlx_profile_id", "")
    return out


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
    segments = []
    for raw in steps:
        tokens = shlex.split(raw, posix=posix)
        segments.append(shlex.join([bin_path, "--cdp-url", cdp, *tokens]))
    script = " && ".join(segments)
    proc = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=timeout)
    return UIResult(
        success=proc.returncode == 0,
        command="chain",
        args=steps,
        stdout=(proc.stdout or "")[-8000:],
        stderr=(proc.stderr or "")[-2000:],
        cdp_url=cdp,
        account_id=sess.get("account_id", ""),
    )
