"""Raw CDP workflow over MLX session."""

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.workflows import cdp_control


def test_parse_params_json():
    assert cdp_control.parse_params('{"url": "https://x.com"}') == {"url": "https://x.com"}
    assert cdp_control.parse_params("") == {}


def test_cdp_send_no_session(tmp_path, monkeypatch):
    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    monkeypatch.setattr(
        "nextbrowser_harness.workflows.cdp_control.load_session",
        lambda: {},
    )
    res = cdp_control.cdp_send(cfg, "Page.navigate", {"url": "https://example.com"})
    assert not res.success
    assert "No MLX CDP session" in (res.error or "")


def test_cdp_send_success(tmp_path, monkeypatch):
    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    monkeypatch.setenv(
        "NEXTBROWSER_BROWSER_USE_SESSION",
        str(tmp_path / "sess.json"),
    )
    from nextbrowser_harness.integrations.browser_use.bridge import save_session

    save_session({"cdp_url": "http://127.0.0.1:9222", "account_id": "alice"})

    mock_client = MagicMock()
    mock_client.send.return_value = {"result": {"value": "ok"}}

    class FakePage:
        url = "https://example.com/"

    @contextmanager
    def fake_mlx(*a, **k):
        page = FakePage()
        page.context = MagicMock()
        page.context.pages = [page]
        page.context.new_cdp_session = MagicMock(return_value=mock_client)
        yield page

    with patch("nextbrowser_harness.workflows.cdp_control.mlx_page", fake_mlx):
        res = cdp_control.cdp_send(cfg, "Runtime.evaluate", {"expression": "1+1"})
    assert res.success
    assert res.method == "Runtime.evaluate"
    mock_client.send.assert_called_once_with("Runtime.evaluate", {"expression": "1+1"})


def test_cli_send_json(tmp_path, capsys):
    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    with patch("nextbrowser_harness.workflows.cdp_control.cdp_send") as send_mock:
        send_mock.return_value = cdp_control.CDPResult(
            success=True,
            method="Page.navigate",
            params={"url": "https://a.com"},
            result={},
            cdp_url="http://127.0.0.1:9222",
            account_id="a",
        )
        rc = cdp_control.cli_main(
            cfg,
            ["send", "Page.navigate", "--params", '{"url":"https://a.com"}'],
        )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["success"] is True
