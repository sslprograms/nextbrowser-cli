"""browser-use CDP bridge session helpers."""

import json
from pathlib import Path

import pytest

from nextbrowser_harness.integrations.browser_use.bridge import (
    load_session,
    save_session,
)


def test_save_and_load_session(tmp_path, monkeypatch):
    path = tmp_path / "session.json"
    monkeypatch.setenv("NEXTBROWSER_BROWSER_USE_SESSION", str(path))
    data = {"cdp_url": "http://127.0.0.1:9222", "account_id": "test"}
    save_session(data)
    loaded = load_session()
    assert loaded["cdp_url"] == "http://127.0.0.1:9222"
    assert loaded["account_id"] == "test"


def test_connect_account_mock(tmp_path, monkeypatch):
    from nextbrowser_harness.accounts.registry import AccountRegistry
    from nextbrowser_harness.config import HarnessConfig
    from nextbrowser_harness.integrations.browser_use.bridge import connect_account
    from nextbrowser_harness.integrations.multilogin.client import StartedProfile

    cfg = HarnessConfig(
        profiles_dir=str(tmp_path / "profiles"),
        multilogin={"folder_id": "f1", "profiles": {}},
    )
    AccountRegistry(cfg).register("alice", mlx_profile_id="p1", mlx_folder_id="f1")

    monkeypatch.setenv("NEXTBROWSER_BROWSER_USE_SESSION", str(tmp_path / "bu.json"))

    class FakeClient:
        def start_profile(self, folder_id, profile_id, **kw):
            return StartedProfile(
                profile_id=profile_id,
                folder_id=folder_id,
                port="9222",
                browser_type="mimic",
                raw={},
            )

    monkeypatch.setattr(
        "nextbrowser_harness.integrations.browser_use.bridge.ensure_mlx_launcher_running",
        lambda: {"launcher_reachable_after": True},
    )
    monkeypatch.setattr(
        "nextbrowser_harness.integrations.browser_use.bridge.MultiloginXClient",
        lambda: FakeClient(),
    )
    monkeypatch.setattr(
        "nextbrowser_harness.integrations.browser_use.bridge.browser_use_bin",
        lambda: "/usr/bin/browser-use",
    )

    out = connect_account(cfg, "alice")
    assert out["success"]
    assert out["cdp_url"] == "http://127.0.0.1:9222"
    assert "browser-use --cdp-url" in out["browser_use_prefix"]
    assert load_session()["account_id"] == "alice"
