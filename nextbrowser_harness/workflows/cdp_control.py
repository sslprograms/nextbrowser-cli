"""
Raw Chrome DevTools Protocol (CDP) over Multilogin X.

Requires ``--account <name>`` on every command. No automatic session file load.
"""

from __future__ import annotations

import base64
import json
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

from nextbrowser_harness.accounts.registry import AccountRegistry
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.multilogin.account_cli import (
    AccountRequiredError,
    resolve_account_id,
    resolve_running_cdp,
)
from nextbrowser_harness.integrations.multilogin.playwright_session import mlx_page
from nextbrowser_harness.workflows.browser_intel import infer_logged_in_with_reason


def _eval_value(client: Any, expression: str) -> Any:
    """Runtime.evaluate with returnByValue; raises on exception."""
    raw = client.send(
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": False,
        },
    )
    if raw.get("exceptionDetails"):
        raise RuntimeError(json.dumps(raw["exceptionDetails"], default=str))
    return (raw.get("result") or {}).get("value")


_VIEWPORT_ANALYSIS_JS = """
(() => {
  const vh = window.innerHeight;
  const vw = window.innerWidth;
  const scrollY = window.scrollY;
  const scrollHeight = Math.max(
    document.documentElement.scrollHeight,
    document.body ? document.body.scrollHeight : 0
  );
  const sel = [
    'a[href]', 'button', 'input', 'textarea', 'select', 'summary',
    '[role=button]', '[role=link]', '[role=textbox]', '[role=combobox]',
    '[contenteditable=true]'
  ].join(',');
  const interactive = [];
  for (const el of document.querySelectorAll(sel)) {
    if (interactive.length >= 80) break;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (r.bottom < 0 || r.top > vh) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || s.opacity === '0') continue;
    interactive.push({
      tag: el.tagName.toLowerCase(),
      text: (el.getAttribute('aria-label') || el.placeholder || el.innerText || el.value || '')
        .trim().slice(0, 120),
      href: el.href ? String(el.href).slice(0, 240) : null,
      type: el.getAttribute('type'),
      role: el.getAttribute('role'),
      top: Math.round(r.top),
      left: Math.round(r.left),
    });
  }
  return {
    scrollY: Math.round(scrollY),
    viewportHeight: vh,
    viewportWidth: vw,
    scrollHeight: Math.round(scrollHeight),
    title: document.title,
    url: location.href,
    visibleText: (document.body && document.body.innerText ? document.body.innerText : '').slice(0, 6000),
    interactiveCount: interactive.length,
    interactive,
  };
})()
"""


def _scroll_to(client: Any, y: int) -> None:
    _eval_value(client, f"window.scrollTo({{top: {int(y)}, left: 0, behavior: 'instant'}}); null")


def default_snapshot_dir(account_id: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = re.sub(r"[^\w\-]+", "_", account_id).strip("_") or "account"
    return Path.home() / ".nextbrowser" / "snapshots" / safe / ts


def capture_screenshot_cdp(
    client: Any,
    *,
    save_path: Path | None = None,
    embed_base64: bool = False,
) -> dict[str, Any]:
    """CDP Page.captureScreenshot — save PNG and/or return base64 for vision models."""
    raw = client.send(
        "Page.captureScreenshot",
        {"format": "png", "fromSurface": True, "captureBeyondViewport": False},
    )
    data = ""
    if isinstance(raw, dict):
        data = str(raw.get("data") or "")
    if not data:
        return {"success": False, "error": "empty screenshot data", "raw": raw}

    png = base64.b64decode(data)
    out: dict[str, Any] = {
        "success": True,
        "format": "png",
        "bytes": len(png),
    }
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(png)
        out["path"] = str(save_path.resolve())
    if embed_base64:
        out["base64"] = data
    return out


def cdp_snapshot(
    config: HarnessConfig,
    *,
    account_id: str | None = None,
    use_saved_session: bool = False,
    page_index: int = 0,
    path: str | Path | None = None,
    embed_base64: bool = False,
) -> dict[str, Any]:
    """Single viewport screenshot via CDP (current scroll position)."""
    try:
        aid = resolve_account_id(account_id, use_saved_session=use_saved_session)
        cdp_url, mlx_id, folder_id = resolve_running_cdp(config, aid)
    except Exception as e:
        return {"success": False, "error": str(e)}

    save_path = Path(path) if path else default_snapshot_dir(aid) / "viewport.png"
    try:
        with cdp_session(
            config,
            account_id=aid,
            use_saved_session=use_saved_session,
            page_index=page_index,
        ) as (page, client, cdp_url, aid):
            try:
                client.send("Page.enable", {})
            except Exception:
                pass
            shot = capture_screenshot_cdp(
                client, save_path=save_path, embed_base64=embed_base64
            )
            return {
                "success": shot.get("success", False),
                "account_id": aid,
                "cdp_url": cdp_url,
                "page_url": page.url or "",
                "screenshot": shot,
                "agent_note": (
                    "Open screenshot path with your vision model to understand the page "
                    "before any cdp send actions."
                ),
            }
    except Exception as e:
        return {"success": False, "account_id": aid, "error": str(e)}


def page_survey(
    config: HarnessConfig,
    *,
    account_id: str | None = None,
    use_saved_session: bool = False,
    page_index: int = 0,
    step_ratio: float = 0.85,
    max_segments: int = 50,
    wait_ms: int = 350,
    reset_to_top: bool = True,
    capture_screenshots: bool = True,
    snapshot_dir: str | Path | None = None,
    embed_base64: bool = False,
) -> dict[str, Any]:
    """
    Scroll the full page in viewport steps; analyze + screenshot each stop.

    Agents must read all ``segments`` (text + screenshot paths) before other CDP actions.
    """
    try:
        aid = resolve_account_id(account_id, use_saved_session=use_saved_session)
        cdp_url, mlx_id, folder_id = resolve_running_cdp(config, aid)
    except Exception as e:
        return {"success": False, "error": str(e)}

    step_ratio = max(0.25, min(1.0, float(step_ratio)))
    max_segments = max(1, min(200, int(max_segments)))
    wait_ms = max(0, int(wait_ms))

    segments: list[dict[str, Any]] = []
    shot_dir: Path | None = None
    if capture_screenshots:
        shot_dir = Path(snapshot_dir) if snapshot_dir else default_snapshot_dir(aid)
        shot_dir.mkdir(parents=True, exist_ok=True)

    try:
        with cdp_session(
            config,
            account_id=aid,
            use_saved_session=use_saved_session,
            page_index=page_index,
        ) as (page, client, cdp_url, aid):
            try:
                client.send("Page.enable", {})
            except Exception:
                pass

            _scroll_to(client, 0)
            if wait_ms:
                page.wait_for_timeout(wait_ms)

            first = _eval_value(client, _VIEWPORT_ANALYSIS_JS)
            if not isinstance(first, dict):
                return {
                    "success": False,
                    "error": "viewport analysis returned non-object",
                    "account_id": aid,
                }

            vh = int(first.get("viewportHeight") or 800)
            scroll_height = int(first.get("scrollHeight") or vh)
            step = max(1, int(vh * step_ratio))
            positions: list[int] = []
            y = 0
            while y < scroll_height and len(positions) < max_segments:
                positions.append(y)
                if y + step >= scroll_height:
                    break
                y += step
            if positions[-1] != max(0, scroll_height - vh):
                bottom_y = max(0, scroll_height - vh)
                if bottom_y not in positions:
                    positions.append(bottom_y)

            for idx, scroll_y in enumerate(positions):
                _scroll_to(client, scroll_y)
                if wait_ms:
                    page.wait_for_timeout(wait_ms)
                snap = _eval_value(client, _VIEWPORT_ANALYSIS_JS)
                if not isinstance(snap, dict):
                    snap = {"error": "analysis failed", "scrollY": scroll_y}
                visible = str(snap.get("visibleText") or "")
                url = str(snap.get("url") or page.url or "")
                state_blob = f"Current URL: {url}\n{visible}"
                login_reason, login_hint = infer_logged_in_with_reason(state_blob)
                at_bottom = scroll_y + vh >= scroll_height - 4
                seg: dict[str, Any] = {
                    "index": idx,
                    "scroll_y": int(snap.get("scrollY", scroll_y)),
                    "scroll_y_target": scroll_y,
                    "viewport_height": vh,
                    "scroll_height": scroll_height,
                    "at_page_bottom": at_bottom,
                    "title": snap.get("title", ""),
                    "url": url,
                    "visible_text": visible,
                    "interactive_count": snap.get("interactiveCount", 0),
                    "interactive": snap.get("interactive") or [],
                    "logged_in_hint": login_hint,
                    "logged_in_reason": login_reason,
                }
                if shot_dir:
                    shot_meta = capture_screenshot_cdp(
                        client,
                        save_path=shot_dir / f"segment-{idx:03d}.png",
                        embed_base64=embed_base64,
                    )
                    seg["screenshot"] = shot_meta
                    if shot_meta.get("path"):
                        seg["screenshot_path"] = shot_meta["path"]
                segments.append(seg)

            if reset_to_top:
                _scroll_to(client, 0)
                if wait_ms:
                    page.wait_for_timeout(min(wait_ms, 200))

            return {
                "success": True,
                "account_id": aid,
                "mlx_profile_id": mlx_id,
                "folder_id": folder_id,
                "cdp_url": cdp_url,
                "page_url": page.url or "",
                "policy": (
                    "Before any cdp send on this page: read every segment's visible_text "
                    "AND open each screenshot_path with your vision model (snapshots are ground truth)."
                ),
                "visual_understanding": (
                    "Use PNG snapshots to see layout, colors, and controls — not text alone. "
                    "After actions, run cdp snapshot or cdp survey again to verify."
                ),
                "snapshot_dir": str(shot_dir.resolve()) if shot_dir else None,
                "layout": {
                    "scroll_height": scroll_height,
                    "viewport_height": vh,
                    "viewport_width": int(first.get("viewportWidth") or 0),
                    "step_pixels": step,
                    "segment_count": len(segments),
                },
                "segments": segments,
                "reset_scroll_to_top": reset_to_top,
            }
    except Exception as e:
        return {
            "success": False,
            "account_id": aid,
            "cdp_url": cdp_url,
            "error": str(e),
            "segments": segments,
        }


# ---------------------------------------------------------------------------
# Deterministic CDP login (trusted Input events — works in MLX anti-detect)
# ---------------------------------------------------------------------------

# Tags the best username/password/submit controls with data-nb-login so they can
# be re-focused reliably after layout shifts, and returns their viewport centers.
_DETECT_LOGIN_JS = r"""
(() => {
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || s.opacity === '0') return false;
    return true;
  };
  const attr = (el, n) => (el.getAttribute(n) || '').toLowerCase();
  const hintOf = (el) => [attr(el,'name'), attr(el,'id'), attr(el,'autocomplete'),
                          attr(el,'aria-label'), (el.placeholder||'').toLowerCase()].join(' ');
  document.querySelectorAll('[data-nb-login]').forEach(e => e.removeAttribute('data-nb-login'));

  let password = null;
  for (const el of document.querySelectorAll('input[type=password]')) {
    if (isVisible(el)) { password = el; break; }
  }

  const userCandidates = [];
  for (const el of document.querySelectorAll('input')) {
    const t = (el.getAttribute('type') || 'text').toLowerCase();
    if (['password','hidden','checkbox','radio','submit','button','file','range','color'].includes(t)) continue;
    if (!isVisible(el)) continue;
    const h = hintOf(el);
    if (t === 'search' || /search/.test(h)) continue;
    let score = 0;
    if (el.getAttribute('autocomplete') === 'username') score += 5;
    if (t === 'email' || /e-?mail/.test(h)) score += 3;
    if (/user|login|account|phone|\btel\b/.test(h)) score += 2;
    userCandidates.push({ el, score, top: el.getBoundingClientRect().top });
  }
  userCandidates.sort((a, b) => (b.score - a.score) || (a.top - b.top));
  const username = userCandidates.length ? userCandidates[0].el : null;

  const scope = (password && password.form) || (username && username.form) || document;
  const re = /log ?in|sign ?in|continue|next|submit|let'?s go|done|go/i;
  let submit = null;
  for (const el of scope.querySelectorAll("button, input[type=submit], input[type=button], [role=button]")) {
    if (!isVisible(el)) continue;
    if ((el.getAttribute('type') || '').toLowerCase() === 'submit') { submit = el; break; }
  }
  if (!submit) {
    for (const el of scope.querySelectorAll("button, input[type=button], [role=button]")) {
      if (!isVisible(el)) continue;
      const label = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim();
      if (re.test(label)) { submit = el; break; }
    }
  }

  const pack = (el, key) => {
    if (!el) return { found: false };
    el.setAttribute('data-nb-login', key);
    const r = el.getBoundingClientRect();
    return {
      found: true,
      x: Math.round(r.left + r.width / 2),
      y: Math.round(r.top + r.height / 2),
      tag: el.tagName.toLowerCase(),
      type: (el.getAttribute('type') || ''),
      label: (el.innerText || el.value || el.getAttribute('aria-label') || el.placeholder || '').trim().slice(0, 80),
    };
  };
  return {
    url: location.href,
    title: document.title,
    username: pack(username, 'username'),
    password: pack(password, 'password'),
    submit: pack(submit, 'submit'),
    has_password_field: !!password,
  };
})()
"""

_OBSTACLE_PATTERNS = (
    ("captcha", r"\b(captcha|recaptcha|hcaptcha|are you human|verify you'?re human|i'?m not a robot)\b"),
    ("two_factor", r"\b(two[- ]?factor|2fa|verification code|one[- ]?time (code|password)|otp|authenticator)\b"),
    ("email_verify", r"\b(verify your email|confirm your email|check your inbox)\b"),
)


def _detect_obstacle(blob: str) -> str | None:
    low = (blob or "").lower()
    for name, pat in _OBSTACLE_PATTERNS:
        if re.search(pat, low):
            return name
    return None


def _focus_and_center(client: Any, key: str) -> dict[str, Any]:
    expr = (
        "(() => { const el = document.querySelector('[data-nb-login=\"" + key + "\"]');"
        " if (!el) return {ok:false};"
        " try { el.scrollIntoView({block:'center', inline:'center'}); } catch(e) {}"
        " try { el.focus(); } catch(e) {}"
        " try { if (el.select) el.select(); } catch(e) {}"
        " const r = el.getBoundingClientRect();"
        " return {ok:true, x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)};"
        " })()"
    )
    out = _eval_value(client, expr)
    return out if isinstance(out, dict) else {"ok": False}


def _click_at(client: Any, x: int, y: int) -> None:
    for kind in ("mousePressed", "mouseReleased"):
        client.send(
            "Input.dispatchMouseEvent",
            {"type": kind, "x": int(x), "y": int(y), "button": "left", "clickCount": 1},
        )


def _press_enter(client: Any) -> None:
    base = {"windowsVirtualKeyCode": 13, "key": "Enter", "code": "Enter"}
    client.send("Input.dispatchKeyEvent", {"type": "keyDown", **base})
    client.send("Input.dispatchKeyEvent", {"type": "char", "text": "\r", **base})
    client.send("Input.dispatchKeyEvent", {"type": "keyUp", **base})


def _fill_field(client: Any, key: str, value: str) -> bool:
    """Focus the tagged field, click it (trusted), then insert text (trusted)."""
    pos = _focus_and_center(client, key)
    if not pos.get("ok"):
        return False
    _click_at(client, pos["x"], pos["y"])
    # Re-select existing content so insertText replaces it.
    _eval_value(
        client,
        "(() => { const el = document.activeElement; if (el && el.select) { try { el.select(); } catch(e) {} } return true; })()",
    )
    client.send("Input.insertText", {"text": value})
    return True


def _settle(page: Any, ms: int) -> None:
    if ms <= 0:
        return
    try:
        page.wait_for_timeout(ms)
    except Exception:
        pass


def cdp_login(
    config: HarnessConfig,
    *,
    account_id: str | None = None,
    url: str,
    username: str,
    password: str,
    use_saved_session: bool = False,
    page_index: int = 0,
    submit: bool = True,
    settle_ms: int = 1500,
    capture: bool = True,
    snapshot_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Deterministic login over MLX CDP: navigate, fill credentials with trusted
    Input events, submit, then verify the result. Handles single-page and
    two-step (username → next → password) forms. Never echoes the password.
    """
    try:
        aid = resolve_account_id(account_id, use_saved_session=use_saved_session)
        cdp_url, mlx_id, folder_id = resolve_running_cdp(config, aid)
    except Exception as e:
        return {"success": False, "error": str(e)}

    base_dir = Path(snapshot_dir) if snapshot_dir else default_snapshot_dir(aid)
    steps: list[str] = []
    shots: dict[str, Any] = {}

    def shot(name: str, client: Any) -> None:
        if not capture:
            return
        meta = capture_screenshot_cdp(client, save_path=base_dir / f"{name}.png")
        if meta.get("path"):
            shots[name] = meta["path"]

    try:
        with cdp_session(
            config,
            account_id=aid,
            use_saved_session=use_saved_session,
            page_index=page_index,
        ) as (page, client, cdp_url, aid):
            for m in ("Page.enable", "DOM.enable", "Runtime.enable"):
                try:
                    client.send(m, {})
                except Exception:
                    pass

            if url:
                client.send("Page.navigate", {"url": url})
                _settle(page, settle_ms)
                steps.append("navigate")

            shot("login-before", client)

            detect = _eval_value(client, _DETECT_LOGIN_JS)
            if not isinstance(detect, dict):
                detect = {}
            filled: list[str] = []

            if detect.get("username", {}).get("found") and _fill_field(client, "username", username):
                filled.append("username")
                steps.append("fill_username")

            # Two-step forms: username first, password appears after advancing.
            if password and not detect.get("has_password_field") and "username" in filled:
                if detect.get("submit", {}).get("found") and _focus_and_center(client, "submit").get("ok"):
                    pos = _focus_and_center(client, "submit")
                    _click_at(client, pos["x"], pos["y"])
                    steps.append("advance")
                else:
                    _press_enter(client)
                    steps.append("advance_enter")
                _settle(page, settle_ms)
                detect = _eval_value(client, _DETECT_LOGIN_JS)
                if not isinstance(detect, dict):
                    detect = {}

            if password and detect.get("password", {}).get("found") and _fill_field(client, "password", password):
                filled.append("password")
                steps.append("fill_password")

            submitted = False
            if submit and filled:
                final = _eval_value(client, _DETECT_LOGIN_JS)
                if isinstance(final, dict) and final.get("submit", {}).get("found"):
                    pos = _focus_and_center(client, "submit")
                    if pos.get("ok"):
                        _click_at(client, pos["x"], pos["y"])
                        submitted = True
                        steps.append("submit_click")
                if not submitted:
                    _press_enter(client)
                    submitted = True
                    steps.append("submit_enter")
                _settle(page, settle_ms)

            analysis = _eval_value(client, _VIEWPORT_ANALYSIS_JS)
            if not isinstance(analysis, dict):
                analysis = {}
            page_url = str(analysis.get("url") or page.url or url or "")
            visible = str(analysis.get("visibleText") or "")
            blob = f"Current URL: {page_url}\n{visible}"
            reason, logged_in = infer_logged_in_with_reason(blob)
            obstacle = _detect_obstacle(blob)

            shot("login-after", client)

            if logged_in is True:
                AccountRegistry(config).mark_logged_in(aid, logged_in=True)
            elif logged_in is False:
                AccountRegistry(config).mark_logged_in(aid, logged_in=False)

            fields_found = {
                "username": bool(detect.get("username", {}).get("found")),
                "password": bool(detect.get("password", {}).get("found")),
                "submit": bool(detect.get("submit", {}).get("found")),
            }
            if not filled:
                error = "No login fields filled — username/password fields not found on the page."
            elif obstacle:
                error = f"Login blocked by {obstacle} — finish it in the MLX window, then re-run."
            elif logged_in is False:
                error = "Still logged out after submit (wrong credentials, extra step, or anti-bot block)."
            else:
                error = None

            success = logged_in is True
            out: dict[str, Any] = {
                "success": success,
                "account_id": aid,
                "mlx_profile_id": mlx_id,
                "cdp_url": cdp_url,
                "url": url,
                "page_url": page_url,
                "fields_found": fields_found,
                "filled": filled,
                "submitted": submitted,
                "steps": steps,
                "logged_in": logged_in,
                "logged_in_reason": reason,
                "obstacle": obstacle,
                "screenshots": shots,
                "state": blob[-4000:],
                "error": error,
            }
            if success:
                out["agent_prompt"] = (
                    f"Logged in as '{aid}'. Open screenshots['login-after'] to confirm visually. "
                    f"Continue with cdp send --account {aid}."
                )
            elif logged_in is None:
                out["agent_prompt"] = (
                    "Login result is uncertain. Open screenshots['login-after'] with your vision model "
                    f"and run `nextbrowser cdp survey --account {aid}` to confirm before claiming success."
                )
            else:
                out["agent_prompt"] = (
                    error or "Login did not complete."
                ) + f" Inspect screenshots['login-after'] / `cdp survey --account {aid}`."
            return out
    except Exception as e:
        return {
            "success": False,
            "account_id": aid,
            "cdp_url": cdp_url,
            "url": url,
            "steps": steps,
            "screenshots": shots,
            "error": str(e),
        }


@dataclass
class CDPResult:
    success: bool
    method: str
    params: dict[str, Any]
    result: Any = None
    error: str | None = None
    cdp_url: str = ""
    account_id: str = ""
    page_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_params(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    text = str(raw).strip()
    if text.startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("params JSON must be an object")
        return data
    if "=" in text and not text.startswith("["):
        out: dict[str, Any] = {}
        for part in text.split(","):
            k, _, v = part.partition("=")
            out[k.strip()] = v.strip().strip('"')
        return out
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("params JSON must be an object")
    return data


@contextmanager
def cdp_session(
    config: HarnessConfig,
    *,
    account_id: str,
    use_saved_session: bool = False,
    page_index: int = 0,
) -> Iterator[tuple[Any, Any, str, str]]:
    """Yield (page, CDPSession, cdp_url, account_id)."""
    aid = resolve_account_id(account_id, use_saved_session=use_saved_session)
    cdp_url, _, _ = resolve_running_cdp(config, aid)
    with mlx_page(
        config,
        account_id=aid,
        use_saved_session=use_saved_session,
    ) as page:
        ctx = page.context
        pages = ctx.pages
        if pages and 0 <= page_index < len(pages):
            page = pages[page_index]
        client = ctx.new_cdp_session(page)
        yield page, client, cdp_url, aid


def session_info(
    config: HarnessConfig,
    *,
    account_id: str | None = None,
    use_saved_session: bool = False,
    page_index: int = 0,
) -> dict[str, Any]:
    try:
        aid = resolve_account_id(account_id, use_saved_session=use_saved_session)
    except AccountRequiredError as e:
        return {"connected": False, "error": str(e)}
    try:
        cdp_url, mlx_id, folder_id = resolve_running_cdp(config, aid)
    except Exception as e:
        return {
            "connected": False,
            "account_id": aid,
            "error": str(e),
        }
    try:
        with mlx_page(
            config,
            account_id=aid,
            use_saved_session=use_saved_session,
        ) as page:
            ctx = page.context
            pages = ctx.pages
            if pages and 0 <= page_index < len(pages):
                page = pages[page_index]
            targets = [{"index": i, "url": (p.url or ""), "title": ""} for i, p in enumerate(pages)]
            for i, p in enumerate(pages):
                try:
                    targets[i]["title"] = p.title()
                except Exception:
                    pass
            return {
                "connected": True,
                "connection": "cdp",
                "cdp_url": cdp_url,
                "account_id": aid,
                "mlx_profile_id": mlx_id,
                "folder_id": folder_id,
                "active_page_index": page_index,
                "page_url": page.url or "",
                "targets": targets,
                "session_file": "not used (pass --account on every command)",
            }
    except Exception as e:
        return {
            "connected": True,
            "cdp_url": cdp_url,
            "account_id": aid,
            "error": str(e),
        }


def cdp_send(
    config: HarnessConfig,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    account_id: str | None = None,
    use_saved_session: bool = False,
    page_index: int = 0,
) -> CDPResult:
    method = (method or "").strip()
    prm = dict(params or {})
    if not method:
        return CDPResult(
            success=False,
            method="",
            params=prm,
            error="CDP method name required (e.g. Page.navigate, DOM.getDocument)",
        )
    try:
        aid = resolve_account_id(account_id, use_saved_session=use_saved_session)
        cdp_url, _, _ = resolve_running_cdp(config, aid)
    except Exception as e:
        return CDPResult(
            success=False,
            method=method,
            params=prm,
            error=str(e),
        )
    try:
        with cdp_session(
            config,
            account_id=aid,
            use_saved_session=use_saved_session,
            page_index=page_index,
        ) as (page, client, cdp_url, aid):
            result = client.send(method, prm)
            return CDPResult(
                success=True,
                method=method,
                params=prm,
                result=result,
                cdp_url=cdp_url,
                account_id=aid,
                page_url=page.url or "",
            )
    except Exception as e:
        return CDPResult(
            success=False,
            method=method,
            params=prm,
            error=str(e),
            cdp_url=cdp_url,
            account_id=aid,
        )


CDP_METHOD_CATALOG: dict[str, str] = {
    "Page.navigate": '{"url": "https://example.com"}',
    "Page.captureScreenshot": '{"format": "png", "fromSurface": true}',
    "DOM.getDocument": '{"depth": -1, "pierce": true}',
    "Runtime.evaluate": '{"expression": "document.title", "returnByValue": true}',
    "Input.dispatchMouseEvent": (
        '{"type": "mousePressed", "x": 100, "y": 200, "button": "left", "clickCount": 1}'
    ),
}


def catalog() -> dict[str, Any]:
    return {
        "note": "Examples only. Agent must call each method via `cdp send --account <name>`.",
        "methods": CDP_METHOD_CATALOG,
    }


def cli_main(config: HarnessConfig, argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="nextbrowser cdp")
    p.add_argument(
        "--account",
        help="Registered MLX account name (required unless --use-saved-session)",
    )
    p.add_argument(
        "--use-saved-session",
        action="store_true",
        help="Load account from session file written by connect --persist-session",
    )
    sub = p.add_subparsers(dest="cdp_cmd", required=True)

    p_sess = sub.add_parser("session", help="CDP URL, active page, targets")
    p_sess.add_argument("--page-index", type=int, default=0)
    p_survey = sub.add_parser(
        "survey",
        help="Scroll full page viewport-by-viewport; analyze each slice (run before actions)",
    )
    p_survey.add_argument("--page-index", type=int, default=0)
    p_survey.add_argument(
        "--step-ratio",
        type=float,
        default=0.85,
        help="Fraction of viewport height per scroll step (default 0.85)",
    )
    p_survey.add_argument(
        "--max-segments",
        type=int,
        default=50,
        help="Cap viewport slices (default 50)",
    )
    p_survey.add_argument(
        "--wait-ms",
        type=int,
        default=350,
        help="Pause after each scroll before analysis (default 350)",
    )
    p_survey.add_argument(
        "--no-reset-top",
        action="store_true",
        help="Leave scroll position at last segment instead of returning to top",
    )
    p_survey.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Skip Page.captureScreenshot per segment (not recommended)",
    )
    p_survey.add_argument(
        "--snapshot-dir",
        default="",
        help="Directory for PNG files (default ~/.nextbrowser/snapshots/<account>/<ts>/)",
    )
    p_survey.add_argument(
        "--embed-base64",
        action="store_true",
        help="Include base64 PNG in JSON (large; use when agent cannot read files)",
    )
    p_snap = sub.add_parser(
        "snapshot",
        help="CDP screenshot of current viewport (vision / verification)",
    )
    p_snap.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Output PNG path (default under ~/.nextbrowser/snapshots/)",
    )
    p_snap.add_argument("--page-index", type=int, default=0)
    p_snap.add_argument("--embed-base64", action="store_true")
    p_nav = sub.add_parser(
        "navigate",
        help="Page.navigate + full-page survey (CDP open URL the right way)",
    )
    p_nav.add_argument("url", help="URL to open")
    p_nav.add_argument("--no-survey", action="store_true")
    sub.add_parser("catalog", help="Example CDP methods (not executed)")

    p_send = sub.add_parser("send", help="Send one CDP method")
    p_send.add_argument("method", help="e.g. Page.navigate, DOM.getDocument")
    p_send.add_argument("--params", "-p", default="")
    p_send.add_argument("--params-file", default="")
    p_send.add_argument("--page-index", type=int, default=0)

    ns, extra = p.parse_known_args(argv)
    if extra:
        print(json.dumps({"error": f"unknown arguments: {extra}"}, indent=2))
        return 1

    if ns.cdp_cmd == "session":
        out = session_info(
            config,
            account_id=ns.account,
            use_saved_session=ns.use_saved_session,
            page_index=ns.page_index,
        )
        print(json.dumps(out, indent=2))
        return 0 if out.get("connected") else 1

    if ns.cdp_cmd == "catalog":
        print(json.dumps(catalog(), indent=2))
        return 0

    if ns.cdp_cmd == "navigate":
        nav = cdp_send(
            config,
            "Page.navigate",
            {"url": ns.url},
            account_id=ns.account,
            use_saved_session=ns.use_saved_session,
        )
        out: dict[str, Any] = {
            "success": nav.success,
            "account_id": nav.account_id,
            "cdp_url": nav.cdp_url,
            "navigate": nav.to_dict(),
        }
        if not nav.success:
            out["error"] = nav.error
            print(json.dumps(out, indent=2, default=str))
            return 1
        if not ns.no_survey:
            survey = page_survey(
                config,
                account_id=ns.account,
                use_saved_session=ns.use_saved_session,
            )
            out["survey"] = survey
            out["success"] = bool(survey.get("success"))
            if not out["success"]:
                out["error"] = survey.get("error")
        print(json.dumps(out, indent=2, default=str))
        return 0 if out.get("success") else 1

    if ns.cdp_cmd == "survey":
        snap_dir = ns.snapshot_dir.strip() or None
        out = page_survey(
            config,
            account_id=ns.account,
            use_saved_session=ns.use_saved_session,
            page_index=ns.page_index,
            step_ratio=ns.step_ratio,
            max_segments=ns.max_segments,
            wait_ms=ns.wait_ms,
            reset_to_top=not ns.no_reset_top,
            capture_screenshots=not ns.no_screenshots,
            snapshot_dir=snap_dir,
            embed_base64=ns.embed_base64,
        )
        print(json.dumps(out, indent=2, default=str))
        return 0 if out.get("success") else 1

    if ns.cdp_cmd == "snapshot":
        out = cdp_snapshot(
            config,
            account_id=ns.account,
            use_saved_session=ns.use_saved_session,
            page_index=ns.page_index,
            path=ns.path,
            embed_base64=ns.embed_base64,
        )
        print(json.dumps(out, indent=2, default=str))
        return 0 if out.get("success") else 1

    if ns.cdp_cmd == "send":
        if ns.params_file:
            prm = json.loads(Path(ns.params_file).read_text(encoding="utf-8"))
        else:
            prm = parse_params(ns.params)
        res = cdp_send(
            config,
            ns.method,
            prm,
            account_id=ns.account,
            use_saved_session=ns.use_saved_session,
            page_index=ns.page_index,
        )
        print(json.dumps(res.to_dict(), indent=2, default=str))
        return 0 if res.success else 1

    return 1
