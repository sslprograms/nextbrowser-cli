"""
Built-in per-site action recipes — agents load by domain + flow name.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

RECIPES_DIR = Path(__file__).resolve().parent / "recipes"


def _recipe_files() -> list[Path]:
    if not RECIPES_DIR.is_dir():
        return []
    return sorted(RECIPES_DIR.glob("*.json"))


def domain_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def resolve_recipe_id(recipe_id: str, url: str = "") -> tuple[str, str]:
    """
    Parse recipe id: 'reddit.com/login', 'reddit.login', or 'login' (domain from url).
    """
    rid = (recipe_id or "").strip()
    if not rid:
        raise ValueError("recipe id required")
    if "/" in rid:
        site, flow = rid.split("/", 1)
        return site.strip(), flow.strip()
    if "." in rid and rid.split(".", 1)[0] not in ("login", "upvote", "signup"):
        site, flow = rid.split(".", 1)
        return site.strip(), flow.strip()
    site = domain_from_url(url) if url else ""
    if not site:
        raise ValueError(f"Cannot infer site for recipe '{rid}' — pass URL or use site/flow form")
    return site, rid


def load_recipe(site: str) -> dict[str, Any]:
    path = RECIPES_DIR / f"{site}.json"
    if not path.is_file():
        for p in _recipe_files():
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("site") == site:
                return data
        raise FileNotFoundError(f"No recipe for site '{site}' (looked in {RECIPES_DIR})")
    return json.loads(path.read_text(encoding="utf-8"))


def _substitute_vars(text: str, variables: dict[str, str]) -> str:
    out = text
    for key, val in variables.items():
        out = out.replace("{" + key + "}", val)
        out = out.replace("{{" + key + "}}", val)
    return out


def _flow_to_actions(flow: dict[str, Any], variables: dict[str, str]) -> list[str]:
    if "actions" in flow:
        raw = flow["actions"]
    elif flow.get("selector") and flow.get("shadow_button"):
        host = flow["selector"]
        btn = flow["shadow_button"]
        check = flow.get("check", "")
        actions = [f"deep-click:{host} >> {btn}"]
        if check:
            actions.insert(0, f"eval:!({check})")
        return [_substitute_vars(a, variables) for a in actions]
    else:
        raise ValueError("Recipe flow must have 'actions' or upvote-style selector block")

    return [_substitute_vars(str(a), variables) for a in raw]


def expand_recipe(
    recipe_id: str,
    *,
    url: str = "",
    variables: dict[str, str] | None = None,
) -> tuple[str | None, list[str]]:
    """
    Return (start_url, action strings) for exec --recipe.
    variables: username, password, etc. replace {username} in recipe strings.
    """
    site, flow_name = resolve_recipe_id(recipe_id, url)
    data = load_recipe(site)
    flows = data.get("flows") or {}
    if flow_name not in flows:
        # legacy: top-level login/upvote keys
        if flow_name in data and isinstance(data[flow_name], dict):
            flow = data[flow_name]
        else:
            raise KeyError(f"Flow '{flow_name}' not in recipe for {site}")
    else:
        flow = flows[flow_name]

    start_url = flow.get("url") or data.get("url") or url or None
    if start_url:
        start_url = _substitute_vars(str(start_url), variables or {})
    actions = _flow_to_actions(flow, variables or {})
    return (start_url, actions)


def list_recipes() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for path in _recipe_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        site = data.get("site") or path.stem
        flows = data.get("flows") or {}
        for name, flow in flows.items():
            if isinstance(flow, dict):
                out.append({"site": site, "flow": name, "id": f"{site}/{name}"})
        for key in ("login", "upvote", "signup"):
            if key in data and isinstance(data[key], dict) and key not in flows:
                out.append({"site": site, "flow": key, "id": f"{site}/{key}"})
    return out
