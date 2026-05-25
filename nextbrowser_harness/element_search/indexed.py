"""
Indexed element map for AI agents — browser-use-style UX without the browser-use package.

Builds a numbered list of interactive elements (accessibility + DOM scan, including shadow roots),
returns text for the agent via ``state``, and acts by index through Playwright.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


class IndexedElementSearchError(Exception):
    pass


_ATTR = "data-nb-index"


@dataclass
class IndexedElement:
    index: int
    role: str
    name: str
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)


_BUILD_SCRIPT = """
() => {
  const ATTR = 'data-nb-index';
  document.querySelectorAll('[' + ATTR + ']').forEach(el => el.removeAttribute(ATTR));

  const interactiveSelector = [
    'a[href]', 'button', 'input', 'textarea', 'select', 'summary',
    '[role=button]', '[role=link]', '[role=textbox]', '[role=combobox]',
    '[role=checkbox]', '[role=radio]', '[role=menuitem]', '[role=tab]',
    '[contenteditable=true]', 'faceplate-text-input', 'faceplate-button'
  ].join(',');

  function isVisible(el) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  }

  function labelOf(el) {
    return (
      el.getAttribute('aria-label') ||
      el.getAttribute('placeholder') ||
      el.getAttribute('title') ||
      el.getAttribute('name') ||
      el.getAttribute('id') ||
      (el.innerText || el.textContent || '').trim().slice(0, 80) ||
      ''
    );
  }

  function roleOf(el) {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (tag === 'a') return 'link';
    if (tag === 'button') return 'button';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'select') return 'combobox';
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'submit' || t === 'button') return 'button';
      return 'textbox';
    }
    if (tag.includes('faceplate')) return tag;
    return tag;
  }

  const seen = new Set();
  const out = [];
  let idx = 1;

  function consider(el) {
    if (!el || seen.has(el) || !isVisible(el)) return;
    seen.add(el);
    el.setAttribute(ATTR, String(idx));
    const innerInput = el.matches('input, textarea')
      ? el
      : el.querySelector('input, textarea');
    out.push({
      index: idx,
      role: roleOf(el),
      name: labelOf(innerInput || el),
      tag: el.tagName.toLowerCase(),
      attrs: {
        id: el.id || '',
        type: el.getAttribute('type') || '',
        name: el.getAttribute('name') || '',
      },
    });
    idx += 1;
  }

  function walk(root) {
    try {
      root.querySelectorAll(interactiveSelector).forEach(consider);
    } catch (e) {}
    root.querySelectorAll('*').forEach((el) => {
      if (el.shadowRoot) walk(el.shadowRoot);
    });
  }

  walk(document);
  return out;
}
"""


class IndexedElementSearch:
    """Sync indexed element map on a Playwright page (no external browser-use lib)."""

    def __init__(self, page) -> None:
        self.page = page
        self._map: dict[int, IndexedElement] = {}
        self._state_refreshed = False

    def refresh_state(self) -> str:
        raw = self.page.evaluate(_BUILD_SCRIPT)
        self._map = {}
        for item in raw or []:
            i = int(item["index"])
            self._map[i] = IndexedElement(
                index=i,
                role=str(item.get("role") or ""),
                name=str(item.get("name") or "").strip(),
                tag=str(item.get("tag") or ""),
                attrs={k: str(v) for k, v in (item.get("attrs") or {}).items()},
            )
        self._state_refreshed = True
        return self.format_for_agent()

    def format_for_agent(self) -> str:
        """Text block for the agent (same idea as browser-use llm_representation)."""
        if not self._map:
            return "No interactive elements found. Try wait_load or scroll, then state again."
        lines = [
            "Interactive elements (use click:N and type:N|value — run state again after navigation):",
            "",
        ]
        for i in sorted(self._map):
            el = self._map[i]
            label = el.name.replace("\n", " ").strip() or "(no label)"
            lines.append(f"[{i}] {el.role} <{el.tag}> {label}")
        return "\n".join(lines)

    def get_map(self) -> dict[int, IndexedElement]:
        return dict(self._map)

    def find_indices(self, query: str, *, limit: int = 10) -> list[int]:
        q = query.strip().lower()
        if not q:
            return []
        hits: list[int] = []
        for i, el in sorted(self._map.items()):
            blob = f"{el.role} {el.tag} {el.name} {el.attrs.get('id','')} {el.attrs.get('name','')}".lower()
            if q in blob:
                hits.append(i)
                if len(hits) >= limit:
                    break
        return hits

    def wait_for_index(self, index: int, *, timeout_ms: int = 30_000) -> None:
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            self.refresh_state()
            if index in self._map:
                return
            time.sleep(0.4)
        raise IndexedElementSearchError(
            f"Index {index} not found within {timeout_ms}ms — run state after navigation"
        )

    def _locator_for(self, index: int):
        if index not in self._map:
            if not self._state_refreshed:
                self.refresh_state()
            if index not in self._map:
                raise IndexedElementSearchError(
                    f"Element index {index} not in map — page may have changed. Run action state first."
                )
        return self.page.locator(f"[{_ATTR}='{index}']")

    def click(self, index: int) -> str:
        if index < 1:
            raise IndexedElementSearchError("Element index must be >= 1")
        if not self._state_refreshed:
            self.refresh_state()
        loc = self._locator_for(index)
        el = self._map[index]
        target = loc
        if el.tag not in ("input", "textarea", "select"):
            inner = loc.locator("input, textarea, button, a, [role=button]").first
            try:
                if inner.count() > 0:
                    target = inner
            except Exception:
                pass
        target.click(timeout=30_000)
        return f"clicked [{index}] {el.role} {el.name[:60]}"

    def input_text(self, index: int, text: str, *, clear: bool = True) -> str:
        if not self._state_refreshed:
            self.refresh_state()
        loc = self._locator_for(index)
        el = self._map[index]
        target = loc
        if el.tag not in ("input", "textarea"):
            inner = loc.locator("input, textarea").first
            try:
                if inner.count() > 0:
                    target = inner
            except Exception:
                pass
        target.click(timeout=15_000)
        if clear:
            try:
                target.fill("", timeout=10_000)
            except Exception:
                pass
        self.page.keyboard.type(text, delay=50)
        return f"typed into [{index}] {el.role}"

    def to_json_summary(self) -> str:
        return json.dumps(
            [
                {"index": el.index, "role": el.role, "tag": el.tag, "name": el.name, "attrs": el.attrs}
                for _, el in sorted(self._map.items())
            ],
            ensure_ascii=False,
        )
