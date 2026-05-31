"""Deterministic CDP login engine (trusted Input events, verify result)."""

import base64
from contextlib import contextmanager

from nextbrowser_harness.accounts.registry import AccountRegistry
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.workflows import cdp_control


class FakePage:
    url = "https://example.com/home"

    def wait_for_timeout(self, ms):  # noqa: D401 - test stub
        return None


class FakeClient:
    def __init__(self):
        self.inserted = []
        self.mouse = []
        self.keys = []
        self.navigated = []

    def send(self, method, params=None):
        params = params or {}
        if method == "Runtime.evaluate":
            return {"result": {"value": self._evaluate(params.get("expression", ""))}}
        if method == "Page.captureScreenshot":
            return {"data": base64.b64encode(b"PNG").decode()}
        if method == "Input.insertText":
            self.inserted.append(params.get("text"))
        elif method == "Input.dispatchMouseEvent":
            self.mouse.append((params.get("type"), params.get("x"), params.get("y")))
        elif method == "Input.dispatchKeyEvent":
            self.keys.append(params.get("type"))
        elif method == "Page.navigate":
            self.navigated.append(params.get("url"))
        return {}

    def _evaluate(self, expr):
        if "interactiveCount" in expr:  # _VIEWPORT_ANALYSIS_JS — verification
            return {
                "url": "https://example.com/home",
                "title": "Home",
                "visibleText": "Welcome back. Log out  Profile  Settings",
                "interactiveCount": 3,
                "interactive": [],
            }
        if "has_password_field" in expr:  # _DETECT_LOGIN_JS
            return {
                "url": "https://example.com/login",
                "title": "Sign in",
                "username": {"found": True, "x": 100, "y": 120},
                "password": {"found": True, "x": 100, "y": 160},
                "submit": {"found": True, "x": 100, "y": 200},
                "has_password_field": True,
            }
        if "activeElement" in expr:  # select-before-insert
            return True
        if "data-nb-login" in expr:  # _focus_and_center
            return {"ok": True, "x": 100, "y": 120}
        return None


@contextmanager
def _fake_session(*args, **kwargs):
    yield FakePage(), FakeClient(), "http://127.0.0.1:9222", "alice"


def _cfg(tmp_path):
    return HarnessConfig(
        profiles_dir=str(tmp_path / "profiles"),
        multilogin={"folder_id": "f1", "profiles": {}},
    )


def test_cdp_login_fills_submits_and_verifies(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    AccountRegistry(cfg).register("alice", mlx_profile_id="prof-1", mlx_folder_id="f1")

    captured = {}

    @contextmanager
    def session(*args, **kwargs):
        client = FakeClient()
        captured["client"] = client
        yield FakePage(), client, "http://127.0.0.1:9222", "alice"

    monkeypatch.setattr(cdp_control, "resolve_account_id", lambda *a, **k: "alice")
    monkeypatch.setattr(
        cdp_control, "resolve_running_cdp", lambda cfg, aid: ("http://127.0.0.1:9222", "prof-1", "f1")
    )
    monkeypatch.setattr(cdp_control, "cdp_session", session)

    out = cdp_control.cdp_login(
        cfg,
        account_id="alice",
        url="https://example.com/login",
        username="alice@example.com",
        password="s3cret-pass",
        settle_ms=0,
        snapshot_dir=str(tmp_path / "shots"),
    )

    assert out["success"] is True
    assert out["logged_in"] is True
    assert out["filled"] == ["username", "password"]
    assert out["submitted"] is True
    client = captured["client"]
    # Credentials typed with trusted Input.insertText (not via JS value set).
    assert "alice@example.com" in client.inserted
    assert "s3cret-pass" in client.inserted
    # Before + after screenshots saved.
    assert "login-before" in out["screenshots"]
    assert "login-after" in out["screenshots"]
    # Registry marked logged in.
    assert AccountRegistry(cfg).get("alice").logged_in is True


def test_cdp_login_reports_logged_out(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    AccountRegistry(cfg).register("alice", mlx_profile_id="prof-1", mlx_folder_id="f1")

    class LoggedOutClient(FakeClient):
        def _evaluate(self, expr):
            if "interactiveCount" in expr:
                return {
                    "url": "https://example.com/login",
                    "title": "Sign in",
                    "visibleText": "Log in  Sign up  Forgot password",
                    "interactiveCount": 3,
                    "interactive": [],
                }
            return super()._evaluate(expr)

    @contextmanager
    def session(*args, **kwargs):
        yield FakePage(), LoggedOutClient(), "http://127.0.0.1:9222", "alice"

    monkeypatch.setattr(cdp_control, "resolve_account_id", lambda *a, **k: "alice")
    monkeypatch.setattr(
        cdp_control, "resolve_running_cdp", lambda cfg, aid: ("http://127.0.0.1:9222", "prof-1", "f1")
    )
    monkeypatch.setattr(cdp_control, "cdp_session", session)

    out = cdp_control.cdp_login(
        cfg,
        account_id="alice",
        url="https://example.com/login",
        username="alice@example.com",
        password="wrong",
        settle_ms=0,
        snapshot_dir=str(tmp_path / "shots"),
    )

    assert out["success"] is False
    assert out["logged_in"] is False
    assert "logged out" in (out["error"] or "").lower()
    assert AccountRegistry(cfg).get("alice").logged_in is False
