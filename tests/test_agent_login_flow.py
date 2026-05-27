"""Agent-run login preamble and credential gating."""

from unittest.mock import patch

from nextbrowser_harness.agent.preflight import PreflightResult
from nextbrowser_harness.agent.runner import (
    _build_task_with_login,
    _build_system_prompt,
    run_agent,
)
from nextbrowser_harness.config import HarnessConfig


def test_build_task_injects_login_block_when_logged_out():
    task = _build_task_with_login(
        "Post a comment",
        url="https://example.com/r/foo",
        logged_in_live=False,
        has_credentials=True,
    )
    assert "mandatory_first_steps" in task.lower()
    assert "Post a comment" in task


def test_build_system_prompt_includes_credentials_policy():
    _, extend = _build_system_prompt(
        account_id="alice",
        has_credentials=True,
        require_login=True,
        logged_in_live=False,
    )
    assert "credentials_login_policy" in extend
    assert "using_credentials" in extend


def test_run_agent_fails_fast_without_creds_when_logged_out(tmp_path):
    cfg = HarnessConfig(
        profiles_dir=str(tmp_path / "profiles"),
        multilogin={"folder_id": "f1", "profiles": {}},
    )
    with patch("nextbrowser_harness.agent.runner.connect_account") as conn, patch(
        "nextbrowser_harness.agent.runner.probe_login_state"
    ) as probe:
        conn.return_value = {"cdp_url": "http://127.0.0.1:9222"}
        probe.return_value = PreflightResult(
            logged_in_likely=False,
            explanation="auth gate",
            state_snippet="Log in",
            browser_use_ok=True,
        )
        res = run_agent(
            cfg,
            "do something",
            account_id="alice",
            url="https://example.com",
        )
    assert not res.success
    assert "no credentials" in (res.error or "").lower()
