"""Indexed element search parsing and helpers (no browser-use package)."""

from unittest.mock import MagicMock

from nextbrowser_harness.browser_actions import (
    ActionSpec,
    parse_element_index,
    spec_uses_indexed_element,
)
from nextbrowser_harness.element_search.context import resolve_element_search_mode
from nextbrowser_harness.element_search.indexed import IndexedElement, IndexedElementSearch
from nextbrowser_harness.config import HarnessConfig


def test_parse_element_index():
    assert parse_element_index("5") == 5
    assert parse_element_index("@12") == 12
    assert parse_element_index("0") is None
    assert parse_element_index("#x") is None


def test_spec_uses_indexed_element():
    assert spec_uses_indexed_element(ActionSpec.parse("click:5"), "indexed")
    assert not spec_uses_indexed_element(ActionSpec.parse("click:#id"), "indexed")
    assert spec_uses_indexed_element(ActionSpec.parse("type:3|hello"), "indexed")
    assert spec_uses_indexed_element(ActionSpec.parse("state"), "indexed")
    assert not spec_uses_indexed_element(ActionSpec.parse("click:5"), "playwright")


def test_resolve_element_search_defaults_indexed():
    cfg = HarnessConfig()
    assert resolve_element_search_mode(cfg) == "indexed"


def test_resolve_element_search_playwright_override():
    cfg = HarnessConfig()
    assert resolve_element_search_mode(cfg, override="playwright") == "playwright"


def test_resolve_browser_use_alias_maps_to_indexed(monkeypatch):
    monkeypatch.setenv("NEXTBROWSER_ELEMENT_SEARCH", "browser_use")
    cfg = HarnessConfig()
    assert resolve_element_search_mode(cfg) == "indexed"


def test_format_for_agent():
    search = IndexedElementSearch(MagicMock())
    search._map = {
        1: IndexedElement(1, "button", "Sign in", "button", {}),
        2: IndexedElement(2, "textbox", "Username", "input", {}),
    }
    text = search.format_for_agent()
    assert "[1]" in text
    assert "Sign in" in text
    assert "[2]" in text


def test_find_indices():
    search = IndexedElementSearch(MagicMock())
    search._map = {
        3: IndexedElement(3, "textbox", "Username", "input", {}),
        4: IndexedElement(4, "textbox", "Password", "input", {}),
    }
    assert search.find_indices("password") == [4]


def test_action_spec_state_and_find():
    assert ActionSpec.parse("state").type == "state"
    f = ActionSpec.parse("find:login button")
    assert f.type == "find"
    assert f.value == "login button"
