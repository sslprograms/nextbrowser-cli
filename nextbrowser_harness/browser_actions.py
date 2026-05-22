"""
Shared browser action runner for browse / exec — used by OpenClaw and other agents via CLI.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class BrowseActionResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ActionSpec:
    type: str
    expression: str = ""
    path: str = ""
    selector: str = ""
    value: str = ""
    ms: int = 0
    url: str = ""

    @classmethod
    def parse(cls, raw: str | dict[str, Any]) -> ActionSpec:
        if isinstance(raw, dict):
            t = str(raw.get("type", "")).lower()
            return cls(
                type=t,
                expression=str(raw.get("expression") or raw.get("js") or ""),
                path=str(raw.get("path") or raw.get("jsfile") or ""),
                selector=str(raw.get("selector", "")),
                value=str(raw.get("value", "")),
                ms=int(raw.get("ms") or raw.get("timeout") or 0),
                url=str(raw.get("url", "")),
            )
        s = (raw or "").strip()
        if not s:
            return cls(type="noop")
        if ":" in s:
            kind, rest = s.split(":", 1)
            kind = kind.lower()
            if kind == "eval":
                return cls(type="eval", expression=rest)
            if kind in ("jsfile", "js-file", "script"):
                return cls(type="jsfile", path=rest.strip())
            if kind == "click":
                return cls(type="click", selector=rest.strip())
            if kind == "fill":
                if "|" in rest:
                    sel, val = rest.split("|", 1)
                    return cls(type="fill", selector=sel.strip(), value=val)
                return cls(type="fill", selector=rest.strip(), value="")
            if kind == "wait":
                return cls(type="wait", ms=int(rest.strip() or "1000"))
            if kind == "goto":
                return cls(type="goto", url=rest.strip())
        return cls(type=s.lower())


def load_steps_file(path: str | Path) -> list[ActionSpec]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [ActionSpec.parse(x) for x in data]
    actions = data.get("actions") or []
    return [ActionSpec.parse(x) for x in actions]


def run_action(page, spec: ActionSpec, *, default_url: str = "", screenshot: str | None = None) -> BrowseActionResult:
    """Run one action on a Playwright page."""
    try:
        if spec.type == "goto":
            target = spec.url or default_url
            page.goto(target, wait_until="domcontentloaded", timeout=120_000)
            return BrowseActionResult("goto", True, page.url)
        if spec.type == "wait_load":
            page.wait_for_load_state("networkidle", timeout=30_000)
            return BrowseActionResult("wait_load", True)
        if spec.type == "wait":
            page.wait_for_timeout(max(spec.ms, 100))
            return BrowseActionResult("wait", True, str(spec.ms))
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
            page.locator(spec.selector).first.click(timeout=30_000)
            return BrowseActionResult("click", True, spec.selector)
        if spec.type == "fill":
            page.locator(spec.selector).first.fill(spec.value, timeout=30_000)
            return BrowseActionResult("fill", True, f"{spec.selector}={spec.value[:80]}")
        if spec.type == "screenshot":
            path = spec.path or screenshot or ""
            if not path:
                return BrowseActionResult("screenshot", False, "no path")
            page.screenshot(path=path, full_page=False)
            return BrowseActionResult("screenshot", True, path)
        if spec.type == "reddit_feed_check":
            n = page.locator("article, [data-testid='post-container'], .Post").count()
            return BrowseActionResult("reddit_feed_check", n > 0, f"post-like nodes={n}")
        if spec.type == "noop":
            return BrowseActionResult("noop", True)
        return BrowseActionResult(spec.type, False, "unknown action type")
    except Exception as e:
        return BrowseActionResult(spec.type, False, str(e))


def run_actions(page, specs: list[ActionSpec], *, default_url: str = "", screenshot: str | None = None) -> list[BrowseActionResult]:
    out: list[BrowseActionResult] = []
    for spec in specs:
        out.append(run_action(page, spec, default_url=default_url, screenshot=screenshot))
    return out
