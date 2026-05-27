"""
Raw Chrome DevTools Protocol (CDP) over Multilogin X — no indexed-element shortcuts.

The host agent issues explicit CDP methods (Page.navigate, DOM.*, Input.*, Runtime.*, …)
via Playwright's CDP session attached to the MLX browser target.
"""

from __future__ import annotations

import json
from pathlib import Path
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any, Iterator

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.integrations.browser_use.bridge import load_session
from nextbrowser_harness.integrations.multilogin.playwright_session import mlx_page


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


def _sess_meta() -> tuple[dict[str, Any], str, str]:
    sess = load_session() or {}
    return sess, sess.get("cdp_url", "") or "", sess.get("account_id", "") or ""


def parse_params(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    text = str(raw).strip()
    if text.startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("params JSON must be an object")
        return data
    # Allow bare key=value for simple cases
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
    account_id: str | None = None,
    page_index: int = 0,
) -> Iterator[tuple[Any, Any, str, str]]:
    """Yield (page, CDPSession, cdp_url, account_id)."""
    sess, cdp_url, aid = _sess_meta()
    if not cdp_url:
        raise RuntimeError(
            "No MLX CDP session. Run: nextbrowser connect --account <name>"
        )
    aid = account_id or aid
    with mlx_page(config, account_id=aid) as page:
        ctx = page.context
        pages = ctx.pages
        if pages and 0 <= page_index < len(pages):
            page = pages[page_index]
        client = ctx.new_cdp_session(page)
        yield page, client, cdp_url, aid


def session_info(
    config: HarnessConfig,
    *,
    page_index: int = 0,
) -> dict[str, Any]:
    sess, cdp_url, aid = _sess_meta()
    if not cdp_url:
        return {
            "connected": False,
            "error": "No MLX CDP session. Run: nextbrowser connect --account <name>",
        }
    try:
        with mlx_page(config, account_id=aid) as page:
            ctx = page.context
            pages = ctx.pages
            if pages and 0 <= page_index < len(pages):
                page = pages[page_index]
            targets = [
                {"index": i, "url": (p.url or ""), "title": ""}
                for i, p in enumerate(pages)
            ]
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
                "mlx_profile_id": sess.get("mlx_profile_id", ""),
                "active_page_index": page_index,
                "page_url": page.url or "",
                "targets": targets,
                "control": "Use `nextbrowser cdp send <Domain.method> --params '{...}'`",
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
    page_index: int = 0,
) -> CDPResult:
    method = (method or "").strip()
    if not method:
        return CDPResult(
            success=False,
            method="",
            params=params or {},
            error="CDP method name required (e.g. Page.navigate, DOM.getDocument)",
        )
    prm = dict(params or {})
    _, cdp_url, aid = _sess_meta()
    if not cdp_url:
        return CDPResult(
            success=False,
            method=method,
            params=prm,
            error="No MLX CDP session. Run: nextbrowser connect --account <name>",
        )
    try:
        with cdp_session(config, account_id=aid, page_index=page_index) as (
            page,
            client,
            cdp_url,
            aid,
        ):
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


# Common CDP methods agents use (documentation only — not executed as a bundle)
CDP_METHOD_CATALOG: dict[str, str] = {
    "Page.navigate": '{"url": "https://example.com"}',
    "Page.captureScreenshot": '{"format": "png"}',
    "Page.getLayoutMetrics": "{}",
    "DOM.getDocument": '{"depth": -1, "pierce": true}',
    "DOM.querySelector": '{"nodeId": 1, "selector": "button"}',
    "DOM.getBoxModel": '{"nodeId": <from querySelector>}',
    "Runtime.evaluate": '{"expression": "document.title", "returnByValue": true}',
    "Input.dispatchMouseEvent": (
        '{"type": "mousePressed", "x": 100, "y": 200, "button": "left", "clickCount": 1}'
    ),
    "Input.dispatchKeyEvent": (
        '{"type": "keyDown", "text": "a", "key": "a", "code": "KeyA"}'
    ),
    "Network.enable": "{}",
    "Accessibility.getFullAXTree": "{}",
}


def catalog() -> dict[str, Any]:
    return {
        "note": "Examples only. Agent must call each method via `cdp send`.",
        "methods": CDP_METHOD_CATALOG,
    }


def cli_main(config: HarnessConfig, argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="nextbrowser cdp")
    sub = p.add_subparsers(dest="cdp_cmd", required=True)

    p_sess = sub.add_parser("session", help="CDP URL, active page, targets")
    p_sess.add_argument("--page-index", type=int, default=0)
    sub.add_parser("catalog", help="Example CDP methods (not executed)")

    p_send = sub.add_parser("send", help="Send one CDP method")
    p_send.add_argument("method", help="e.g. Page.navigate, DOM.getDocument")
    p_send.add_argument(
        "--params",
        "-p",
        default="",
        help='JSON object, e.g. \'{"url":"https://example.com"}\'',
    )
    p_send.add_argument(
        "--params-file",
        help="Path to JSON file with CDP params object",
    )
    p_send.add_argument(
        "--page-index",
        type=int,
        default=0,
        help="Which tab in the MLX browser (0 = first)",
    )

    ns = p.parse_args(argv)

    if ns.cdp_cmd == "session":
        print(json.dumps(session_info(config, page_index=ns.page_index), indent=2))
        return 0

    if ns.cdp_cmd == "catalog":
        print(json.dumps(catalog(), indent=2))
        return 0

    if ns.cdp_cmd == "send":
        if ns.params_file:
            prm = json.loads(Path(ns.params_file).read_text(encoding="utf-8"))
        else:
            prm = parse_params(ns.params)
        res = cdp_send(
            config,
            ns.method,
            prm,
            page_index=ns.page_index,
        )
        print(json.dumps(res.to_dict(), indent=2, default=str))
        return 0 if res.success else 1

    return 1
