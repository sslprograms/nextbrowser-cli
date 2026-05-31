"""CDP-only login workflow."""

from unittest.mock import patch

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.workflows.browser_intel import infer_logged_in_from_state
from nextbrowser_harness.workflows.cdp_control import CDPResult
from nextbrowser_harness.workflows.login import login


def _cfg(tmp_path):
    return HarnessConfig(
        profiles_dir=str(tmp_path / "profiles"),
        multilogin={"folder_id": "f1", "profiles": {}},
    )


def test_login_rejects_placeholder_credentials(tmp_path):
    cfg = _cfg(tmp_path)
    res = login(
        cfg,
        "alice",
        url="https://example.com",
        username="USER",
        password="real",
        create_if_missing=False,
    )
    assert not res.success
    assert "placeholder" in res.error.lower()


def test_login_happy_path_cdp(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    from nextbrowser_harness.accounts.registry import AccountRegistry

    AccountRegistry(cfg).register("alice", mlx_profile_id="prof-1", mlx_folder_id="f1")

    with patch("nextbrowser_harness.workflows.login.connect_account") as connect_mock, patch(
        "nextbrowser_harness.workflows.login.cdp_send"
    ) as send_mock, patch(
        "nextbrowser_harness.workflows.login.page_survey"
    ) as survey_mock:
        connect_mock.return_value = {
            "success": True,
            "cdp_url": "http://127.0.0.1:9222",
            "account_id": "alice",
        }
        send_mock.return_value = CDPResult(
            success=True,
            method="Page.navigate",
            params={"url": "https://example.com/home"},
            cdp_url="http://127.0.0.1:9222",
            account_id="alice",
        )
        survey_mock.return_value = {
            "success": True,
            "segments": [
                {
                    "visible_text": "Log out",
                    "logged_in_hint": True,
                }
            ],
        }

        res = login(cfg, "alice", url="https://example.com/home")

    assert res.success
    assert "cdp:Page.navigate" in res.actions_run
    assert "cdp:survey" in res.actions_run
    assert any("cdp survey" in c for c in res.next_commands)
    assert not any("ui " in c for c in res.next_commands)


def test_infer_logged_in_from_state_detects_login_page():
    state = "Current URL: https://example.com/login\n[1]<button>Sign in</button>"
    assert infer_logged_in_from_state(state) is False


def test_infer_logged_in_from_state_detects_logged_in_ui():
    state = "Current URL: https://example.com/home\n[8]<button>Log out</button>"
    assert infer_logged_in_from_state(state) is True
