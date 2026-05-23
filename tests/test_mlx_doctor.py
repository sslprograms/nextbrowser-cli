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
        report = mlx_doctor_report(client)

    assert "next_steps" in report
    assert report["api_token_ok"] is True
    assert report["ok"] is True
