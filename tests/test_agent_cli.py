"""MLX-native passthrough (connect / state / click)."""

from nextbrowser_harness.integrations.browser_use.agent_cli import (
    BROWSER_USE_VERBS,
    is_browser_use_verb,
    try_dispatch_native_browser_use,
)


def test_browser_use_verbs():
    assert is_browser_use_verb("state")
    assert is_browser_use_verb("click")
    assert not is_browser_use_verb("status")


def test_passthrough_without_session(tmp_path, monkeypatch):
    from nextbrowser_harness.config import HarnessConfig

    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    monkeypatch.setenv("NEXTBROWSER_BROWSER_USE_SESSION", str(tmp_path / "missing.json"))
    rc = try_dispatch_native_browser_use(cfg, ["state"])
    assert rc == 1
