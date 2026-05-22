import hashlib
from unittest.mock import MagicMock, patch

import pytest

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


def test_resolve_profile_requires_ids(monkeypatch):
    from nextbrowser_harness.config import HarnessConfig
    from nextbrowser_harness.integrations.multilogin.browser import MultiloginBrowserLayer

    monkeypatch.delenv("MULTILOGIN_FOLDER_ID", raising=False)
    monkeypatch.delenv("MULTILOGIN_PROFILE_ID", raising=False)
    layer = MultiloginBrowserLayer(HarnessConfig(browser="multilogin"), client=MultiloginXClient(token="x"))
    with pytest.raises(MultiloginXError):
        layer.resolve_profile_id("acct1")
