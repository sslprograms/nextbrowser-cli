"""Multilogin platform hints work on all supported OS names."""

from nextbrowser_harness.integrations.multilogin.platform_hints import (
    mlx_setup_script_hint,
    mlx_start_desktop_hint,
)


def test_mlx_hints_non_empty():
    assert mlx_setup_script_hint()
    assert mlx_start_desktop_hint()


def test_mlx_setup_script_path_matches_os(monkeypatch):
    from nextbrowser_harness.integrations.multilogin import platform_hints as ph

    monkeypatch.setattr(ph, "is_windows", lambda: True)
    assert str(ph.mlx_setup_script_path()).endswith("setup-multilogin.ps1")

    monkeypatch.setattr(ph, "is_windows", lambda: False)
    assert str(ph.mlx_setup_script_path()).endswith("setup-multilogin.sh")
