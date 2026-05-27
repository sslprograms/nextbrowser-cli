"""Per-account browser-use session naming."""

from nextbrowser_harness.workflows.browser_use_exec import (
    bu_argv,
    session_name_for_account,
)


def test_session_name_sanitizes_account():
    assert session_name_for_account("Pale-Accident-6750") == "Pale-Accident-6750"
    assert session_name_for_account("foo bar!!!") == "foo-bar"


def test_bu_argv_includes_session():
    argv = bu_argv("/bin/bu", "http://127.0.0.1:9222", ["state"], account_id="alice")
    assert "--session" in argv
    assert "alice" in argv
