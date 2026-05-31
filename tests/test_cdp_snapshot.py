"""CDP Page.captureScreenshot."""

import base64
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.workflows.cdp_control import capture_screenshot_cdp, cdp_snapshot


def test_capture_screenshot_cdp_writes_file(tmp_path):
    client = MagicMock()
    png = b"\x89PNG\x0d\x0a"
    client.send.return_value = {"data": base64.b64encode(png).decode()}
    out_path = tmp_path / "shot.png"
    meta = capture_screenshot_cdp(client, save_path=out_path)
    assert meta["success"]
    assert out_path.read_bytes() == png


def test_cdp_snapshot_cli(tmp_path, capsys):
    cfg = HarnessConfig(profiles_dir=str(tmp_path))
    with patch("nextbrowser_harness.workflows.cdp_control.cdp_snapshot") as snap:
        snap.return_value = {
            "success": True,
            "screenshot": {"path": str(tmp_path / "v.png")},
        }
        from nextbrowser_harness.workflows import cdp_control

        rc = cdp_control.cli_main(
            cfg, ["--account", "alice", "snapshot", str(tmp_path / "v.png")]
        )
    assert rc == 0
