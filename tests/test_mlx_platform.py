"""Multilogin platform hints work on all supported OS names."""

from nextbrowser_harness.integrations.multilogin.platform_hints import (
    ensure_display_linux,
    mlx_install_check,
    mlx_setup_script_hint,
    mlx_setup_wizard_command,
    mlx_start_desktop_hint,
)


def test_mlx_hints_non_empty():
    assert mlx_setup_script_hint()
    assert mlx_start_desktop_hint()
    assert mlx_setup_wizard_command() == "nextbrowser multilogin setup-wizard"


def test_mlx_setup_script_path_matches_os(monkeypatch):
    from nextbrowser_harness.integrations.multilogin import platform_hints as ph

    monkeypatch.setattr(ph, "is_windows", lambda: True)
    assert str(ph.mlx_setup_script_path()).endswith("setup-multilogin.ps1")

    monkeypatch.setattr(ph, "is_windows", lambda: False)
    assert str(ph.mlx_setup_script_path()).endswith("setup-multilogin.sh")


def test_mlx_install_check_returns_structure():
    result = mlx_install_check()
    assert "installed" in result
    assert "checked_paths" in result


def test_ensure_display_linux_on_windows():
    result = ensure_display_linux()
    assert result["display_ok"] is True
