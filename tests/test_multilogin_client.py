import hashlib
from unittest.mock import MagicMock, patch

import pytest
import yaml

from nextbrowser_harness.integrations.multilogin.client import (
    MultiloginXClient,
    MultiloginXError,
    _parse_api_error,
    _signin_password,
)

def test_parse_api_error_message():
    class R:
        text = '{"status":{"message":"Incorrect credentials","error_code":"BAD_REQUEST_VALUES"}}'

        def json(self):
            return {
                "status": {
                    "message": "Incorrect credentials",
                    "error_code": "BAD_REQUEST_VALUES",
                }
            }

    assert "Incorrect credentials" in _parse_api_error(R())


def test_signin_password_md5():
    assert _signin_password("pass") == hashlib.md5(b"pass").hexdigest()


def test_signin_clears_stale_automation_token(tmp_path):
    token_path = tmp_path / "tokens.yaml"
    token_path.write_text(
        yaml.safe_dump({"automation_token": "stale-auto", "token": "old-session"}),
        encoding="utf-8",
    )
    client = MultiloginXClient(token_path=token_path)
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = '{"data": {"token": "fresh", "refresh_token": "ref"}}'
    mock_resp.json.return_value = {"data": {"token": "fresh", "refresh_token": "ref"}}

    with patch("nextbrowser_harness.integrations.multilogin.client.requests.request", return_value=mock_resp):
        client.signin("u@x.com", "pass")

    saved = yaml.safe_load(token_path.read_text(encoding="utf-8"))
    assert saved.get("token") == "fresh"
    assert "automation_token" not in saved


def test_load_prefers_session_token_over_automation(tmp_path):
    token_path = tmp_path / "tokens.yaml"
    token_path.write_text(
        yaml.safe_dump({"automation_token": "auto", "token": "session"}),
        encoding="utf-8",
    )
    client = MultiloginXClient(token_path=token_path)
    assert client._token == "session"


def test_profile_running_uses_status_when_active_missing(tmp_path):
    client = MultiloginXClient(token="tok")
    status_resp = MagicMock()
    status_resp.ok = True
    status_resp.json.return_value = {
        "data": {
            "status": "browser_running",
            "port": 62120,
            "folder_id": "folder-uuid",
            "browser_type": "mimic",
        }
    }

    with patch.object(client, "profile_active", return_value=None):
        with patch(
            "nextbrowser_harness.integrations.multilogin.client.requests.request",
            return_value=status_resp,
        ):
            running = client.profile_running("profile-uuid", folder_id="folder-uuid")

    assert running is not None
    assert running.cdp_url == "http://127.0.0.1:62120"


def test_signin_saves_token(tmp_path):
    client = MultiloginXClient(token_path=tmp_path / "tokens.yaml")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = '{"data": {"token": "abc", "refresh_token": "ref"}}'
    mock_resp.json.return_value = {"data": {"token": "abc", "refresh_token": "ref"}}

    with patch("nextbrowser_harness.integrations.multilogin.client.requests.request", return_value=mock_resp) as req:
        token = client.signin("u@x.com", "pass")

    assert token == "abc"
    assert (tmp_path / "tokens.yaml").exists()
    saved = yaml.safe_load((tmp_path / "tokens.yaml").read_text(encoding="utf-8"))
    assert saved.get("email") == "u@x.com"
    body = req.call_args.kwargs.get("json") or req.call_args[1].get("json")
    assert body["password"] == hashlib.md5(b"pass").hexdigest()


def test_start_profile_parses_port():
    client = MultiloginXClient(token="tok")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "data": {"port": "55513", "browser_type": "mimic"},
        "status": {"http_code": 200},
    }

    with patch("nextbrowser_harness.integrations.multilogin.client.requests.request", return_value=mock_resp):
        started = client.start_profile("folder-uuid", "profile-uuid")

    assert started.cdp_url == "http://127.0.0.1:55513"
    assert started.port == "55513"


def test_refresh_sends_authorization_header(tmp_path, monkeypatch):
    monkeypatch.delenv("MULTILOGIN_EMAIL", raising=False)
    token_path = tmp_path / "tokens.yaml"
    token_path.write_text(
        yaml.safe_dump({"token": "old-access", "refresh_token": "ref123", "email": "u@x.com"}),
        encoding="utf-8",
    )
    client = MultiloginXClient(token_path=token_path)
    client._token = None  # force refresh path

    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = '{"data": {"token": "new-access", "refresh_token": "ref123"}}'
    mock_resp.json.return_value = {"data": {"token": "new-access", "refresh_token": "ref123"}}

    with patch("nextbrowser_harness.integrations.multilogin.client.requests.request", return_value=mock_resp) as req:
        token = client.refresh()

    assert token == "new-access"
    headers = req.call_args.kwargs.get("headers") or req.call_args[1].get("headers")
    assert headers.get("Authorization") == "Bearer old-access"
    body = req.call_args.kwargs.get("json") or req.call_args[1].get("json")
    assert body["refresh_token"] == "ref123"
    assert body["email"] == "u@x.com"


def test_request_401_retries_with_refreshed_token(tmp_path):
    token_path = tmp_path / "tokens.yaml"
    token_path.write_text(
        yaml.safe_dump({"token": "expired", "refresh_token": "ref123", "email": "u@x.com"}),
        encoding="utf-8",
    )
    client = MultiloginXClient(token="expired", token_path=token_path)

    unauthorized = MagicMock()
    unauthorized.ok = False
    unauthorized.status_code = 401
    unauthorized.text = '{"status":{"message":"Unauthorized"}}'
    unauthorized.json.return_value = {"status": {"message": "Unauthorized"}}

    refresh_resp = MagicMock()
    refresh_resp.ok = True
    refresh_resp.status_code = 200
    refresh_resp.text = '{"data": {"token": "fresh", "refresh_token": "ref123"}}'
    refresh_resp.json.return_value = {"data": {"token": "fresh", "refresh_token": "ref123"}}

    ok_resp = MagicMock()
    ok_resp.ok = True
    ok_resp.status_code = 200
    ok_resp.text = '{"data": {"folders": []}}'
    ok_resp.json.return_value = {"data": {"folders": []}}

    with patch(
        "nextbrowser_harness.integrations.multilogin.client.requests.request",
        side_effect=[unauthorized, refresh_resp, ok_resp],
    ) as req:
        folders = client.list_folders()

    assert folders == []
    calls = req.call_args_list
    assert calls[0].kwargs.get("headers", {}).get("Authorization") == "Bearer expired"
    assert calls[1].kwargs.get("headers", {}).get("Authorization") == "Bearer expired"
    assert calls[2].kwargs.get("headers", {}).get("Authorization") == "Bearer fresh"


def test_resolve_profile_requires_ids(monkeypatch):
    from nextbrowser_harness.config import HarnessConfig
    from nextbrowser_harness.integrations.multilogin.browser import MultiloginBrowserLayer

    monkeypatch.delenv("MULTILOGIN_FOLDER_ID", raising=False)
    monkeypatch.delenv("MULTILOGIN_PROFILE_ID", raising=False)
    layer = MultiloginBrowserLayer(HarnessConfig(browser="multilogin"), client=MultiloginXClient(token="x"))
    with pytest.raises(MultiloginXError):
        layer.resolve_profile_id("acct1")
