"""Tier-3 exec requires Multilogin account + credentials when logging in."""

import pytest

from nextbrowser_harness.accounts.registry import AccountRegistry, Tier3AccountError
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.workflows.tier3_gate import (
    action_needs_credentials,
    prepare_tier3_automation,
    recipe_needs_credentials,
)


def test_tier3_requires_account(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path / "profiles"))
    with pytest.raises(Tier3AccountError) as exc:
        prepare_tier3_automation(cfg, resolved_tier=3, account_key="")
    assert exc.value.code == "account_required"
    assert "Which saved account" in exc.value.agent_prompt


def test_tier3_with_registered_account(tmp_path):
    cfg = HarnessConfig(
        profiles_dir=str(tmp_path / "profiles"),
        multilogin={"folder_id": "folder-1", "profiles": {}},
    )
    reg = AccountRegistry(cfg)
    reg.register("alice", mlx_profile_id="prof-uuid-1", mlx_folder_id="folder-1")

    run_cfg, acc, meta = prepare_tier3_automation(
        cfg, resolved_tier=3, account_key="alice", actions=["goto", "state"]
    )
    assert acc is not None
    assert acc.account_id == "alice"
    assert run_cfg.browser == "multilogin"
    assert meta["connection"] == "cdp"


def test_tier2_skips_gate(tmp_path):
    cfg = HarnessConfig(profiles_dir=str(tmp_path / "profiles"))
    run_cfg, acc, meta = prepare_tier3_automation(cfg, resolved_tier=2, account_key="")
    assert acc is None
    assert meta == {}
    assert run_cfg.browser == cfg.browser


def test_recipe_login_needs_credentials():
    assert recipe_needs_credentials("reddit.com/login", None)
    assert recipe_needs_credentials(
        "reddit.com/login", {"username": "USER", "password": "x"}
    )
    assert not recipe_needs_credentials(
        "reddit.com/login", {"username": "real@x.com", "password": "secret"}
    )


def test_action_type_placeholder():
    assert action_needs_credentials(['type:3|USER', "click:1"])
    assert not action_needs_credentials(['type:3|hello', "click:1"])
