"""
Agent UI over Multilogin X + Playwright CDP (indexed elements).

No browser-use CLI, no browser-use API key. Any AgentSkills host agent:
  nextbrowser connect --account <name>
  nextbrowser ui state | click N | type N "text"
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from nextbrowser_harness.accounts.registry import AccountRegistry
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.browser_use.bridge import disconnect_account, load_session
from nextbrowser_harness.integrations.multilogin.playwright_session import (
    capture_state_text,
    mlx_page,
)
from nextbrowser_harness.workflows.browser_intel import (
    agent_gates,
    build_situation_from_state_text,
    text_visible_in_state,
)


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


_ALIASES = {"type": "input", "fill": "input", "submit": "click"}


def _resolve_cmd(name: str) -> str:
    return _ALIASES.get(name, name)


def _sess_meta() -> tuple[dict[str, Any], str, str]:
    sess = load_session() or {}
    return sess, sess.get("cdp_url", "") or "", sess.get("account_id", "") or ""


def run(
    config: HarnessConfig,
    command: str,
    *,
    args: list[str] | None = None,
    timeout: int = 60,
) -> UIResult:
    """MLX + Playwright indexed control (state / click / input / open / scroll)."""
    sess, cdp, aid = _sess_meta()
    if not cdp:
        return UIResult(
            success=False,
            command=command,
            args=args or [],
            error="No MLX session. Run: nextbrowser connect --account <name>",
        )

    cmd = _resolve_cmd(command)
    cmd_args = list(args or [])
    _ = timeout  # page ops use Playwright timeouts

    try:
        with mlx_page(config, account_id=aid) as page:
            from nextbrowser_harness.element_search.indexed import (
                IndexedElementSearch,
                IndexedElementSearchError,
            )

            driver = IndexedElementSearch(page)

            if cmd == "open":
                if not cmd_args:
                    return UIResult(
                        success=False,
                        command=command,
                        args=cmd_args,
                        cdp_url=cdp,
                        account_id=aid,
                        error="url required",
                    )
                page.goto(cmd_args[0], wait_until="domcontentloaded", timeout=90_000)
                out = capture_state_text(page)
                return UIResult(
                    success=True,
                    command=command,
                    args=cmd_args,
                    stdout=out[-8000:],
                    cdp_url=cdp,
                    account_id=aid,
                )

            if cmd == "state":
                out = capture_state_text(page)
                return UIResult(
                    success=True,
                    command=command,
                    args=cmd_args,
                    stdout=out[-8000:],
                    cdp_url=cdp,
                    account_id=aid,
                )

            if cmd == "click":
                if not cmd_args:
                    return UIResult(
                        success=False,
                        command=command,
                        args=cmd_args,
                        cdp_url=cdp,
                        account_id=aid,
                        error="index required",
                    )
                detail = driver.click(int(cmd_args[0]))
                return UIResult(
                    success=True,
                    command=command,
                    args=cmd_args,
                    stdout=detail,
                    cdp_url=cdp,
                    account_id=aid,
                )

            if cmd == "input":
                if len(cmd_args) < 2:
                    return UIResult(
                        success=False,
                        command=command,
                        args=cmd_args,
                        cdp_url=cdp,
                        account_id=aid,
                        error='usage: input <index> "text"',
                    )
                detail = driver.input_text(int(cmd_args[0]), cmd_args[1])
                return UIResult(
                    success=True,
                    command=command,
                    args=cmd_args,
                    stdout=detail,
                    cdp_url=cdp,
                    account_id=aid,
                )

            if cmd == "scroll":
                direction = (cmd_args[0] if cmd_args else "down").lower()
                delta = -600 if direction == "up" else 600
                page.mouse.wheel(0, delta)
                return UIResult(
                    success=True,
                    command=command,
                    args=cmd_args,
                    stdout=f"scrolled {direction}",
                    cdp_url=cdp,
                    account_id=aid,
                )

            if cmd == "keys":
                combo = cmd_args[0] if cmd_args else "Enter"
                page.keyboard.press(combo)
                return UIResult(
                    success=True,
                    command=command,
                    args=cmd_args,
                    stdout=f"keys {combo}",
                    cdp_url=cdp,
                    account_id=aid,
                )

            if cmd == "eval":
                if not cmd_args:
                    return UIResult(
                        success=False,
                        command=command,
                        args=cmd_args,
                        error="javascript required",
                    )
                result = page.evaluate(cmd_args[0])
                return UIResult(
                    success=True,
                    command=command,
                    args=cmd_args,
                    stdout=str(result)[:8000],
                    cdp_url=cdp,
                    account_id=aid,
                )

            if cmd == "screenshot":
                path = cmd_args[0] if cmd_args else "screenshot.png"
                page.screenshot(path=path)
                return UIResult(
                    success=True,
                    command=command,
                    args=cmd_args,
                    stdout=f"saved {path}",
                    cdp_url=cdp,
                    account_id=aid,
                )

            return UIResult(
                success=False,
                command=command,
                args=cmd_args,
                error=f"unknown command: {command}",
                cdp_url=cdp,
                account_id=aid,
            )

    except IndexedElementSearchError as e:
        return UIResult(
            success=False,
            command=command,
            args=cmd_args,
            cdp_url=cdp,
            account_id=aid,
            error=str(e),
        )
    except Exception as e:
        return UIResult(
            success=False,
            command=command,
            args=cmd_args,
            cdp_url=cdp,
            account_id=aid,
            error=str(e),
        )


def situation(
    config: HarnessConfig,
    *,
    timeout: int = 60,
    strict: bool = True,
) -> dict[str, Any]:
    sess, cdp, aid = _sess_meta()
    if not cdp:
        return {
            "connected": False,
            "error": "No MLX session. Run: nextbrowser connect --account <name>",
        }
    reg = AccountRegistry(config).get(aid)
    logged_r = bool(reg.logged_in) if reg else False
    _ = timeout
    try:
        with mlx_page(config, account_id=aid) as page:
            text = capture_state_text(page)
        snap = build_situation_from_state_text(
            text,
            account_id=aid,
            registry_logged_in=logged_r,
            browser_use_exit_code=0,
        )
        out = snap.to_dict()
        out["engine"] = "mlx+playwright"
        out["mlx_profile_id"] = sess.get("mlx_profile_id", "")
        out["strict"] = strict
        gates = out.get("agent_gates") or {}
        out["cli_should_exit_nonzero"] = bool(
            strict and not gates.get("logged_in_verified")
        )
        return out
    except Exception as e:
        return {
            "connected": True,
            "account_id": aid,
            "error": str(e),
            "engine": "mlx+playwright",
        }


def require_login(config: HarnessConfig, *, timeout: int = 60) -> dict[str, Any]:
    out = situation(config, timeout=timeout, strict=True)
    verified = (out.get("agent_gates") or {}).get("logged_in_verified", False)
    out["require_login_ok"] = verified
    if not verified:
        out["error"] = out.get("error") or "NOT LOGGED IN (MLX live check failed)."
    return out


def verify_text(
    config: HarnessConfig,
    text: str,
    *,
    timeout: int = 60,
    min_len: int = 8,
) -> dict[str, Any]:
    needle = (text or "").strip()
    if len(needle) < min_len:
        return {
            "verified": False,
            "error": f"Need at least {min_len} characters to verify.",
        }
    sess, cdp, aid = _sess_meta()
    if not cdp:
        return {"verified": False, "error": "No MLX session."}
    _ = timeout
    try:
        with mlx_page(config, account_id=aid) as page:
            state_text = capture_state_text(page)
            html = page.content()
        found = text_visible_in_state(state_text, needle, min_len=min_len) or (
            needle.lower() in html.lower()
        )
        return {
            "verified": found,
            "text_needle": needle[:120],
            "account_id": aid,
            "engine": "mlx+playwright",
            "error": None
            if found
            else "Text NOT found on page — do not claim success.",
        }
    except Exception as e:
        return {"verified": False, "error": str(e)}


def scroll(
    config: HarnessConfig,
    direction: str = "down",
    pages: float = 1.0,
    *,
    timeout: int = 60,
) -> UIResult:
    _ = pages
    return run(config, "scroll", args=[direction], timeout=timeout)


def close(config: HarnessConfig) -> dict[str, Any]:
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
    """Run indexed steps in one MLX connection (open/state/click/input)."""
    _ = timeout
    outputs: list[str] = []
    for raw in steps:
        parts = raw.split(maxsplit=1)
        if not parts:
            continue
        verb = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        if verb == "open":
            res = run(config, "open", args=[rest.strip('"')], timeout=120)
        elif verb == "state":
            res = run(config, "state", timeout=120)
        elif verb == "click":
            res = run(config, "click", args=[rest.strip()], timeout=120)
        elif verb in ("input", "type"):
            toks = rest.split(maxsplit=1)
            if len(toks) == 2:
                res = run(config, "input", args=[toks[0], toks[1].strip('"')], timeout=120)
            else:
                res = UIResult(success=False, command=verb, args=[], error="bad input step")
        else:
            res = UIResult(success=False, command=verb, args=[], error="unknown step")
        outputs.append(res.stdout or res.error or "")
        if not res.success:
            return UIResult(
                success=False,
                command="chain",
                args=steps,
                stdout="\n".join(outputs)[-8000:],
                error=res.error,
            )
    return UIResult(success=True, command="chain", args=steps, stdout="\n".join(outputs)[-8000:])
