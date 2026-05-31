"""CDP-only CLI dispatch."""

from nextbrowser_harness.integrations.mlx_cdp.agent_cli import (
    is_legacy_ui_verb,
    try_dispatch_cdp,
)


def test_legacy_verbs_blocked():
    assert is_legacy_ui_verb("state")
    assert is_legacy_ui_verb("click")
    assert is_legacy_ui_verb("close")


def test_state_rejected_with_cdp_instructions(tmp_path, capsys):
    from nextbrowser_harness.config import HarnessConfig

    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    rc = try_dispatch_cdp(
        cfg, ["state", "--account", "alice"]
    )
    assert rc == 1
    import json

    out = json.loads(capsys.readouterr().out)
    assert out["success"] is False
    assert "CDP" in out["error"]
    assert any("cdp send" in x for x in out["use_instead"])


def test_ui_close_rejected(tmp_path, capsys):
    from nextbrowser_harness.config import HarnessConfig

    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    rc = try_dispatch_cdp(cfg, ["close", "--account", "alice"])
    assert rc == 1
