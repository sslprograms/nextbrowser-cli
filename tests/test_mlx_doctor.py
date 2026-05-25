"""MLX doctor report for agents."""

from unittest.mock import MagicMock, patch

from nextbrowser_harness.integrations.multilogin.client import MultiloginXClient
from nextbrowser_harness.integrations.multilogin.doctor import mlx_doctor_report


def test_doctor_report_has_next_steps(monkeypatch):
    monkeypatch.setenv("MULTILOGIN_FOLDER_ID", "folder-1")
    monkeypatch.setenv("MULTILOGIN_PROFILE_ID", "profile-1")
    monkeypatch.setenv("NEXTBROWSER_BROWSER", "multilogin")
    client = MultiloginXClient(token="fake-token")

    with patch("nextbrowser_harness.integrations.multilogin.doctor.requests.get") as get:
        r = MagicMock()
        r.status_code = 200
        get.return_value = r
        with patch(
            "nextbrowser_harness.integrations.multilogin.doctor.mlx_install_check",
            return_value={"installed": True, "checked_paths": [], "download_url": "https://multilogin.com"},
        ):
            with patch(
                "nextbrowser_harness.integrations.multilogin.doctor.ensure_display_linux",
                return_value={"needed": False, "display_ok": True},
            ):
                report = mlx_doctor_report(client)

    assert "next_steps" in report
    assert "setup_wizard_command" in report
    assert report["mlx_app_installed"] is True
    assert report["api_token_ok"] is True
    assert report["ok"] is True
