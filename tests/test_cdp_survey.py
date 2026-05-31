"""Full-page CDP survey (scroll + per-viewport analysis)."""

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.workflows import cdp_control


def test_page_survey_requires_account(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    out = cdp_control.page_survey(cfg, account_id=None)
    assert not out["success"]
    assert "--account" in out["error"]


def test_page_survey_multi_segment(tmp_path, monkeypatch):
    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    monkeypatch.setenv(
        "NEXTBROWSER_MLX_SESSION",
        str(tmp_path / "sess.json"),
    )

    scroll_calls: list[int] = []

    def fake_eval(client, expr):
        if "scrollTo" in expr:
            import re

            m = re.search(r"top:\s*(\d+)", expr)
            if m:
                scroll_calls.append(int(m.group(1)))
            return None
        # viewport analysis
        y = scroll_calls[-1] if scroll_calls else 0
        return {
            "scrollY": y,
            "viewportHeight": 400,
            "viewportWidth": 800,
            "scrollHeight": 1000,
            "title": "T",
            "url": "https://example.com",
            "visibleText": f"block at {y}",
            "interactiveCount": 1,
            "interactive": [{"tag": "button", "text": f"btn-{y}", "top": 10}],
        }

    import base64 as b64

    fake_png = b64.b64encode(b"\x89PNGfake").decode()

    def mock_send(method, params=None):
        params = params or {}
        if method == "Page.captureScreenshot":
            return {"data": fake_png}
        if method == "Page.enable":
            return {}
        if method == "Runtime.evaluate":
            return {"result": {"value": fake_eval(mock_client, params.get("expression", ""))}}
        return {}

    mock_client = MagicMock()
    mock_client.send.side_effect = mock_send

    class FakePage:
        url = "https://example.com/"

        def wait_for_timeout(self, ms):
            pass

    @contextmanager
    def fake_cdp(*a, **k):
        yield FakePage(), mock_client, "http://127.0.0.1:9222", "alice"

    with patch(
        "nextbrowser_harness.workflows.cdp_control.resolve_running_cdp",
        lambda *a, **k: ("http://127.0.0.1:9222", "p1", "f1"),
    ), patch(
        "nextbrowser_harness.workflows.cdp_control.cdp_session",
        fake_cdp,
    ):
        out = cdp_control.page_survey(
            cfg,
            account_id="alice",
            step_ratio=0.5,
            wait_ms=0,
            max_segments=10,
        )

    assert out["success"]
    assert len(out["segments"]) >= 2
    assert out["policy"]
    assert out["segments"][0]["visible_text"].startswith("block at")
    assert out["snapshot_dir"]
    assert out["segments"][0].get("screenshot_path")


def test_cli_survey(tmp_path, capsys):
    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    with patch("nextbrowser_harness.workflows.cdp_control.page_survey") as survey:
        survey.return_value = {"success": True, "segments": [], "layout": {}}
        rc = cdp_control.cli_main(cfg, ["--account", "alice", "survey", "--wait-ms", "0"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["success"]
