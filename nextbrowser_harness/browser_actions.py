"""
Shared browser action runner for browse / exec — used by OpenClaw and other agents via CLI.

With ``element_search=indexed``, click/type/wait-for use a numbered element map (``state``)
for agents — same workflow as browser-use, implemented in this harness (no browser-use package).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from nextbrowser_harness.element_search.context import ElementSearchContext

_DEFAULT_TIMEOUT = 30_000
_TYPE_DELAY_MS = 50

# Substrings that suggest a pipe segment is a selector, not a typed value
_SELECTOR_HINTS = (
    "#",
    ".",
    "[",
    ">>",
    "input",
    "button",
    "textarea",
    "select",
    "faceplate",
    "shreddit",
    "shadow",
    "aria-",
    "role=",
    "has(",
    "svg",
    ":is(",
)


@dataclass
class BrowseActionResult:
    name: str
    ok: bool
    detail: str = ""


def _looks_like_selector(segment: str) -> bool:
    s = segment.strip()
    if not s:
        return False
    low = s.lower()
    if "@" in s and not any(h in low for h in ("#", "[", ">>", "input", "button", "textarea", "faceplate")):
        return False
    if any(h in low for h in _SELECTOR_HINTS):
        if "." in s and s.startswith(".") is False and " ." not in s:
            if "." in s and "@" in s:
                return False
        return True
    if s.endswith(" input") or s.endswith(" textarea"):
        return True
    if s.startswith("."):
        return True
    return False


def _parse_selector_chain(rest: str, *, value_mode: bool) -> tuple[list[str], str]:
    """Split pipe chain into selector fallbacks and optional trailing value."""
    parts = [p.strip() for p in rest.split("|") if p.strip()]
    if not parts:
        return [], ""
    if not value_mode:
        return parts, ""
    if len(parts) == 1:
        return parts, ""
    if len(parts) == 2 and not _looks_like_selector(parts[1]):
        return [parts[0]], parts[1]
    if not _looks_like_selector(parts[-1]):
        return parts[:-1], parts[-1]
    return parts, ""


def _expand_selector_variants(selector: str) -> list[str]:
    """Light-DOM + inner-input variants (shadow paths must use >> explicitly)."""
    s = selector.strip()
    if not s:
        return []
    variants = [s]
    if ">>" not in s:
        if not s.rstrip().endswith("input") and "input" not in s.split()[-1].lower():
            variants.append(f"{s} input")
        if "textarea" not in s.lower():
            variants.append(f"{s} textarea")
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _all_selector_attempts(selectors: list[str]) -> list[str]:
    attempts: list[str] = []
    seen: set[str] = set()
    for sel in selectors:
        for variant in _expand_selector_variants(sel):
            if variant not in seen:
                seen.add(variant)
                attempts.append(variant)
    return attempts


def _first_locator(page, selectors: list[str], *, timeout: int = _DEFAULT_TIMEOUT):
    last_err: Exception | None = None
    per_try = max(timeout // max(len(selectors), 1), 3_000)
    for sel in _all_selector_attempts(selectors):
        loc = page.locator(sel).first
        try:
            loc.wait_for(state="visible", timeout=per_try)
            return loc, sel
        except Exception as e:
            last_err = e
            continue
    msg = selectors[0] if selectors else "(none)"
    raise RuntimeError(f"No element matched selectors: {selectors}") from last_err


def _click(page, selectors: list[str], *, timeout: int = _DEFAULT_TIMEOUT) -> str:
    loc, used = _first_locator(page, selectors, timeout=timeout)
    loc.click(timeout=timeout)
    return used


def _type_into(page, selectors: list[str], value: str, *, delay: int = _TYPE_DELAY_MS) -> str:
    loc, used = _first_locator(page, selectors)
    loc.click(timeout=_DEFAULT_TIMEOUT)
    try:
        tag = loc.evaluate("el => el.tagName.toLowerCase()")
    except Exception:
        tag = ""
    if tag not in ("input", "textarea"):
        inner_sel = f"{used} input, {used} textarea"
        inner = page.locator(inner_sel).first
        try:
            inner.wait_for(state="visible", timeout=5_000)
            inner.click(timeout=10_000)
            inner.fill("", timeout=5_000)
            page.keyboard.type(value, delay=delay)
            return used
        except Exception:
            pass
    try:
        loc.fill("", timeout=5_000)
    except Exception:
        pass
    page.keyboard.type(value, delay=delay)
    return used


def _element_inspect(loc) -> dict[str, Any]:
    return loc.evaluate(
        """el => {
        const kids = Array.from(el.children || []).slice(0, 12).map(c => ({
            tag: c.tagName,
            id: c.id || null,
            class: (c.className && String(c.className).slice(0, 80)) || null,
        }));
        return {
            tag: el.tagName,
            id: el.id || null,
            class: (el.className && String(el.className).slice(0, 120)) || null,
            role: el.getAttribute('role'),
            ariaLabel: el.getAttribute('aria-label'),
            type: el.getAttribute('type'),
            name: el.getAttribute('name'),
            shadowRoot: !!(el.shadowRoot),
            childCount: el.children ? el.children.length : 0,
            children: kids,
        };
    }"""
    )


@dataclass
class ActionSpec:
    type: str
    expression: str = ""
    path: str = ""
    selector: str = ""
    selectors: list[str] = field(default_factory=list)
    value: str = ""
    ms: int = 0
    url: str = ""

    def primary_selector(self) -> str:
        return self.selectors[0] if self.selectors else self.selector

    @classmethod
    def parse(cls, raw: str | dict[str, Any]) -> ActionSpec:
        if isinstance(raw, dict):
            t = str(raw.get("type", "")).lower().replace("-", "_")
            sels = raw.get("selectors") or []
            if not sels and raw.get("selector"):
                sels = [str(raw["selector"])]
            return cls(
                type=t,
                expression=str(raw.get("expression") or raw.get("js") or ""),
                path=str(raw.get("path") or raw.get("jsfile") or ""),
                selector=str(raw.get("selector", "")),
                selectors=[str(x) for x in sels],
                value=str(raw.get("value", "")),
                ms=int(raw.get("ms") or raw.get("timeout") or 0),
                url=str(raw.get("url", "")),
            )
        s = (raw or "").strip()
        if not s:
            return cls(type="noop")
        if ":" in s:
            kind, rest = s.split(":", 1)
            kind = kind.lower().replace("-", "_")
            rest = rest.strip()

            if kind == "eval":
                return cls(type="eval", expression=rest)
            if kind in ("jsfile", "js_file", "script"):
                return cls(type="jsfile", path=rest)
            if kind == "goto":
                return cls(type="goto", url=rest)
            if kind == "wait":
                return cls(type="wait", ms=int(rest or "1000"))
            if kind in ("wait_for", "waitfor"):
                sels, _ = _parse_selector_chain(rest, value_mode=False)
                return cls(type="wait_for", selector=sels[0] if sels else rest, selectors=sels or [rest])
            if kind in ("wait_for_nav", "waitfornav"):
                return cls(type="wait_for_nav", url=rest)
            if kind in ("wait_for_text", "waitfortext"):
                return cls(type="wait_for_text", value=rest)
            if kind in ("click", "deep_click", "deep", "shadow_click"):
                sels, _ = _parse_selector_chain(rest, value_mode=False)
                return cls(type="click", selector=sels[0] if sels else "", selectors=sels)
            if kind == "fill":
                sels, val = _parse_selector_chain(rest, value_mode=True)
                return cls(type="type", selector=sels[0] if sels else "", selectors=sels, value=val)
            if kind == "type":
                sels, val = _parse_selector_chain(rest, value_mode=True)
                return cls(type="type", selector=sels[0] if sels else "", selectors=sels, value=val)
            if kind == "screenshot":
                return cls(type="screenshot", path=rest)
            if kind == "inspect":
                return cls(type="inspect", selector=rest, selectors=[rest] if rest else [])
            if kind in ("inspect_all", "inspectall"):
                return cls(type="inspect_all", selector=rest, selectors=[rest] if rest else [])
            if kind in ("cookie_check", "cookiecheck"):
                parts = [p.strip() for p in rest.split("|")]
                domain = parts[0] if parts else rest
                name = parts[1] if len(parts) > 1 else ""
                return cls(type="cookie_check", selector=domain, value=name)
            if kind in ("logged_in", "loggedin"):
                return cls(type="logged_in", selector=rest)
            if kind == "key":
                return cls(type="key", value=rest or "Enter")
            if kind == "reddit_upvote":
                default = "shreddit-post >> button:has(svg[icon-name='upvote'])"
                sel = rest or default
                return cls(type="click", selector=sel, selectors=[sel])
            if kind == "state":
                return cls(type="state")
            if kind == "find":
                return cls(type="find", value=rest)
        return cls(type=s.lower())


def parse_element_index(text: str) -> int | None:
    """Parse browser-use element index (1-based); supports @5 or 5."""
    t = (text or "").strip().lstrip("@")
    if t.isdigit():
        i = int(t)
        return i if i >= 1 else None
    return None


def spec_uses_indexed_element(spec: ActionSpec, mode: str) -> bool:
    """True when this action uses the numbered element map (not CSS)."""
    if mode != "indexed":
        return False
    if spec.type in ("state", "find"):
        return True
    target = spec.primary_selector()
    if spec.type == "click":
        if spec.selectors and all(parse_element_index(s) is not None for s in spec.selectors):
            return True
        return parse_element_index(target) is not None and not _looks_like_selector(target)
    if spec.type == "type":
        if not spec.selectors:
            return parse_element_index(target) is not None
        if len(spec.selectors) == 1 and parse_element_index(spec.selectors[0]) is not None:
            return True
        return False
    if spec.type == "wait_for":
        return parse_element_index(target) is not None and not _looks_like_selector(target)
    return False


def load_steps_file(path: str | Path) -> tuple[str | None, list[ActionSpec]]:
    """
    Load agent step plan from JSON. Returns optional start URL and action specs.
    Format: {"url": "...", "actions": ["goto", "eval:...", ...]} or a bare actions array.
    """
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if isinstance(data, list):
        return None, [ActionSpec.parse(x) for x in data]
    url = data.get("url") or None
    actions = data.get("actions") or []
    return (str(url) if url else None), [ActionSpec.parse(x) for x in actions]


def _domain_match(cookie_domain: str, target: str) -> bool:
    t = target.lstrip(".").lower()
    d = (cookie_domain or "").lstrip(".").lower()
    return d == t or d.endswith("." + t) or t.endswith(d)


def _check_logged_in(page, domain: str) -> tuple[bool, str]:
    host = domain.lower().replace("www.", "")
    cookies = page.context.cookies()
    for c in cookies:
        if _domain_match(c.get("domain", ""), host):
            name = (c.get("name") or "").lower()
            if "session" in name or "token" in name or name in ("reddit_session", "loid", "token_v2"):
                return True, f"cookie:{c.get('name')}"
    hints = [
        "[data-testid='user-drawer-button']",
        "img[alt*='avatar' i]",
        "#email-collection-tooltip-id",
        "faceplate-tracker[noun='profile']",
    ]
    for sel in hints:
        try:
            if page.locator(sel).first.count() > 0:
                return True, f"element:{sel}"
        except Exception:
            continue
    return False, "no session cookie or profile element"


def run_action(
    page,
    spec: ActionSpec,
    *,
    default_url: str = "",
    screenshot: str | None = None,
    _nav_url_before: str | None = None,
) -> BrowseActionResult:
    """Run one action on a Playwright page."""
    selectors = spec.selectors or ([spec.selector] if spec.selector else [])
    try:
        if spec.type == "goto":
            target = spec.url or default_url
            page.goto(target, wait_until="domcontentloaded", timeout=120_000)
            return BrowseActionResult("goto", True, page.url)
        if spec.type == "wait_load":
            page.wait_for_load_state("networkidle", timeout=_DEFAULT_TIMEOUT)
            return BrowseActionResult("wait_load", True)
        if spec.type == "wait":
            page.wait_for_timeout(max(spec.ms, 100))
            return BrowseActionResult("wait", True, str(spec.ms))
        if spec.type == "wait_for":
            if not selectors:
                return BrowseActionResult("wait_for", False, "no selector")
            _first_locator(page, selectors, timeout=_DEFAULT_TIMEOUT)
            return BrowseActionResult("wait_for", True, spec.primary_selector())
        if spec.type == "wait_for_nav":
            before = _nav_url_before or page.url
            try:
                page.wait_for_function(
                    f"() => window.location.href !== {json.dumps(before)}",
                    timeout=_DEFAULT_TIMEOUT,
                )
            except Exception:
                page.wait_for_load_state("load", timeout=_DEFAULT_TIMEOUT)
            return BrowseActionResult("wait_for_nav", True, page.url)
        if spec.type == "wait_for_text":
            page.get_by_text(spec.value, exact=False).first.wait_for(
                state="visible", timeout=_DEFAULT_TIMEOUT
            )
            return BrowseActionResult("wait_for_text", True, spec.value[:120])
        if spec.type == "title":
            return BrowseActionResult("title", True, page.title() or "")
        if spec.type == "scroll":
            page.evaluate("window.scrollTo(0, Math.min(800, document.body.scrollHeight))")
            return BrowseActionResult("scroll", True, "scrolled ~800px")
        if spec.type == "final_url":
            return BrowseActionResult("final_url", True, page.url)
        if spec.type == "eval":
            result = page.evaluate(spec.expression)
            detail = json.dumps(result, default=str) if result is not None else "null"
            if len(detail) > 2000:
                detail = detail[:2000] + "..."
            return BrowseActionResult("eval", True, detail)
        if spec.type == "jsfile":
            js = Path(spec.path).expanduser().read_text(encoding="utf-8")
            result = page.evaluate(js)
            detail = json.dumps(result, default=str) if result is not None else "ok"
            if len(detail) > 2000:
                detail = detail[:2000] + "..."
            return BrowseActionResult("jsfile", True, detail)
        if spec.type == "click":
            used = _click(page, selectors)
            return BrowseActionResult("click", True, used)
        if spec.type == "type":
            if not spec.value and not selectors:
                return BrowseActionResult("type", False, "missing selector and value")
            used = _type_into(page, selectors, spec.value)
            return BrowseActionResult("type", True, f"{used}={spec.value[:80]}")
        if spec.type == "screenshot":
            path = spec.path or screenshot or ""
            if not path:
                return BrowseActionResult("screenshot", False, "no path")
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=path, full_page=False)
            return BrowseActionResult("screenshot", True, path)
        if spec.type == "inspect":
            if not selectors:
                return BrowseActionResult("inspect", False, "no selector")
            loc, used = _first_locator(page, selectors)
            info = _element_inspect(loc)
            detail = json.dumps(info, default=str)
            return BrowseActionResult("inspect", True, f"{used} {detail[:1800]}")
        if spec.type == "inspect_all":
            sel = spec.primary_selector() or "*"
            locs = page.locator(sel)
            n = min(locs.count(), 20)
            items = []
            for i in range(n):
                try:
                    items.append(_element_inspect(locs.nth(i)))
                except Exception:
                    continue
            detail = json.dumps(items, default=str)
            if len(detail) > 2500:
                detail = detail[:2500] + "..."
            return BrowseActionResult("inspect_all", True, f"count={n} {detail}")
        if spec.type == "cookie_check":
            domain = spec.selector
            name = spec.value
            cookies = page.context.cookies()
            found = [
                c
                for c in cookies
                if _domain_match(c.get("domain", ""), domain)
                and (not name or c.get("name") == name)
            ]
            ok = bool(found)
            detail = json.dumps(found[:3], default=str) if found else "missing"
            return BrowseActionResult("cookie_check", ok, detail[:500])
        if spec.type == "logged_in":
            ok, detail = _check_logged_in(page, spec.selector or urlparse(default_url).netloc)
            return BrowseActionResult("logged_in", ok, detail)
        if spec.type == "key":
            page.keyboard.press(spec.value or "Enter")
            return BrowseActionResult("key", True, spec.value)
        if spec.type == "reddit_feed_check":
            n = page.locator("article, [data-testid='post-container'], .Post").count()
            return BrowseActionResult("reddit_feed_check", n > 0, f"post-like nodes={n}")
        if spec.type == "noop":
            return BrowseActionResult("noop", True)
        return BrowseActionResult(spec.type, False, "unknown action type")
    except Exception as e:
        return BrowseActionResult(spec.type, False, str(e))


def _run_indexed_action(
    driver: Any,
    page,
    spec: ActionSpec,
    *,
    default_url: str = "",
    screenshot: str | None = None,
    _nav_url_before: str | None = None,
) -> BrowseActionResult:
    from nextbrowser_harness.element_search.indexed import IndexedElementSearchError

    try:
        if spec.type == "state":
            text = driver.refresh_state()
            if len(text) > 8000:
                text = text[:8000] + "\n...(truncated)"
            return BrowseActionResult("state", True, text)
        if spec.type == "find":
            if not driver.get_map():
                driver.refresh_state()
            indices = driver.find_indices(spec.value)
            detail = json.dumps({"query": spec.value, "indices": indices})
            return BrowseActionResult("find", bool(indices), detail)
        if spec.type == "click":
            indices = [parse_element_index(s) for s in (spec.selectors or [spec.selector])]
            indices = [i for i in indices if i is not None]
            if not indices:
                raise IndexedElementSearchError("No valid element index for click")
            last_err = None
            for idx in indices:
                try:
                    detail = driver.click(idx)
                    return BrowseActionResult("click", True, f"index={idx} {detail}")
                except Exception as e:
                    last_err = e
            raise last_err or IndexedElementSearchError("click failed")
        if spec.type == "type":
            idx = parse_element_index(spec.primary_selector())
            if idx is None:
                raise IndexedElementSearchError("No valid element index for type")
            detail = driver.input_text(idx, spec.value)
            return BrowseActionResult("type", True, f"index={idx} {detail[:200]}")
        if spec.type == "wait_for":
            idx = parse_element_index(spec.primary_selector())
            if idx is None:
                raise IndexedElementSearchError("wait-for requires numeric index in indexed mode")
            driver.wait_for_index(idx)
            return BrowseActionResult("wait_for", True, str(idx))
        return run_action(
            page,
            spec,
            default_url=default_url,
            screenshot=screenshot,
            _nav_url_before=_nav_url_before,
        )
    except Exception as e:
        return BrowseActionResult(spec.type, False, str(e))


def run_actions(
    page,
    specs: list[ActionSpec],
    *,
    default_url: str = "",
    screenshot: str | None = None,
    element_ctx: ElementSearchContext | None = None,
) -> list[BrowseActionResult]:
    indexed_driver = None
    if element_ctx and element_ctx.mode == "indexed":
        from nextbrowser_harness.element_search.indexed import IndexedElementSearch

        indexed_driver = IndexedElementSearch(page)

    out: list[BrowseActionResult] = []
    for spec in specs:
        nav_before = page.url if spec.type in ("click", "type", "key") else None
        if indexed_driver and spec_uses_indexed_element(spec, "indexed"):
            out.append(
                _run_indexed_action(
                    indexed_driver,
                    page,
                    spec,
                    default_url=default_url,
                    screenshot=screenshot,
                    _nav_url_before=nav_before,
                )
            )
        else:
            out.append(
                run_action(
                    page,
                    spec,
                    default_url=default_url,
                    screenshot=screenshot,
                    _nav_url_before=nav_before,
                )
            )
    return out
