"""MLX CDP bridge session helpers + connect_account."""

from nextbrowser_harness.integrations.mlx_cdp.bridge import (
    load_session,
    save_session,
)


def test_save_and_load_session(tmp_path, monkeypatch):
    path = tmp_path / "session.json"
    monkeypatch.setenv("NEXTBROWSER_MLX_SESSION", str(path))
    data = {"cdp_url": "http://127.0.0.1:9222", "account_id": "test"}
    save_session(data)
    loaded = load_session()
    assert loaded["cdp_url"] == "http://127.0.0.1:9222"
    assert loaded["account_id"] == "test"


def test_connect_account_mock(tmp_path, monkeypatch):
    from nextbrowser_harness.accounts.registry import AccountRegistry
    from nextbrowser_harness.config import HarnessConfig
    from nextbrowser_harness.integrations.mlx_cdp.bridge import connect_account
    from nextbrowser_harness.integrations.multilogin.client import StartedProfile

    cfg = HarnessConfig(
        profiles_dir=str(tmp_path / "profiles"),
        multilogin={"folder_id": "f1", "profiles": {}},
    )
    AccountRegistry(cfg).register("alice", mlx_profile_id="p1", mlx_folder_id="f1")

    monkeypatch.setenv("NEXTBROWSER_MLX_SESSION", str(tmp_path / "mlx.json"))

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
        "nextbrowser_harness.integrations.mlx_cdp.bridge.ensure_mlx_launcher_running",
        lambda: {"launcher_reachable_after": True},
    )
    monkeypatch.setattr(
        "nextbrowser_harness.integrations.mlx_cdp.bridge.MultiloginXClient",
        lambda: FakeClient(),
    )

    out = connect_account(cfg, "alice", persist_session=False)
    assert out["success"]
    assert out.get("session_persisted") is False
    assert out["cdp_url"] == "http://127.0.0.1:9222"
    assert out.get("engine") == "mlx+cdp"
    assert "cdp send" in " ".join(out.get("next_commands", []))
    assert load_session() is None
