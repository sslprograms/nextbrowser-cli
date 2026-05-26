"""One-shot login workflow — placeholders, missing accounts, end-to-end mock."""

from unittest.mock import patch

from nextbrowser_harness.config import HarnessConfig
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


def test_login_requires_url(tmp_path):
    cfg = _cfg(tmp_path)
    res = login(cfg, "alice", url="")
    assert not res.success
    assert "url" in res.error.lower()


def test_login_missing_account_with_no_create_returns_prompt(tmp_path):
    cfg = _cfg(tmp_path)
    res = login(
        cfg,
        "alice",
        url="https://example.com",
        create_if_missing=False,
    )
    assert not res.success
    assert "not registered" in res.error.lower() or "unknown" in res.error.lower()
    assert "account add" in res.agent_prompt


def test_login_happy_path_with_indices(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setenv("NEXTBROWSER_BROWSER_USE_SESSION", str(tmp_path / "session.json"))

    # Pre-register the account so login skips MLX create_profile
    from nextbrowser_harness.accounts.registry import AccountRegistry

    AccountRegistry(cfg).register("alice", mlx_profile_id="prof-1", mlx_folder_id="f1")

    with patch("nextbrowser_harness.workflows.login.connect_account") as connect_mock, patch(
        "nextbrowser_harness.workflows.login._bu_chain"
    ) as chain_mock, patch(
        "nextbrowser_harness.workflows.login.browser_use_bin", return_value="/usr/bin/browser-use"
    ):
        connect_mock.return_value = {
            "success": True,
            "cdp_url": "http://127.0.0.1:9222",
            "account_id": "alice",
        }
        class FakeProc:
            returncode = 0
            stdout = "[1] textbox Username\n[2] textbox Password\n[3] button Log in"
            stderr = ""
        chain_mock.return_value = FakeProc()

        res = login(
            cfg,
            "alice",
            url="https://example.com/login",
            username="real_user",
            password="real_pass",
            username_index=1,
            password_index=2,
            submit_index=3,
        )

    assert res.success
    assert res.cdp_url == "http://127.0.0.1:9222"
    assert "open" in res.actions_run
    assert "click" in res.actions_run
    assert res.next_commands  # tells agent how to continue
    assert "ui" in " ".join(res.next_commands)
