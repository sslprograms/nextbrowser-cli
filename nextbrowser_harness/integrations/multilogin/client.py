"""
Multilogin X API client.

Docs: https://documenter.getpostman.com/view/28533318/2s946h9Cv9
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml

API_BASE = os.getenv("MULTILOGIN_API_BASE", "https://api.multilogin.com")
LAUNCHER_BASE = os.getenv("MULTILOGIN_LAUNCHER_URL", "https://launcher.mlx.yt:45001")
TOKEN_PATH = Path.home() / ".nextbrowser" / "multilogin_tokens.yaml"


class MultiloginXError(Exception):
    pass


def _signin_password(password: str) -> str:
    """
    MLX API expects MD5 hex of the account password (see Multilogin Python help).
    Postman examples show plain text; plain fails with 400 for many accounts.
    Set MULTILOGIN_SIGNIN_PLAIN=1 to send the password unchanged.
    """
    if os.getenv("MULTILOGIN_SIGNIN_PLAIN", "").lower() in ("1", "true", "yes"):
        return password
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def _parse_api_error(resp) -> str:
    """Human-readable message from Multilogin JSON error body."""
    try:
        body = resp.json()
        status = body.get("status") or {}
        msg = status.get("message") or body.get("message")
        code = status.get("error_code") or ""
        if msg and code:
            return f"{msg} ({code})"
        if msg:
            return str(msg)
    except Exception:
        pass
    return (resp.text or "")[:500]


@dataclass
class StartedProfile:
    profile_id: str
    folder_id: str
    port: str | None
    browser_type: str | None
    raw: dict[str, Any]

    @property
    def cdp_url(self) -> str | None:
        """CDP endpoint for Playwright connect_over_cdp."""
        if not self.port:
            return None
        port = str(self.port).strip()
        if port.startswith("http"):
            return port
        return f"http://127.0.0.1:{port}"


class MultiloginXClient:
    """
    Multilogin X API + Launcher.

    Auth options (first match wins):
      1. MULTILOGIN_AUTOMATION_TOKEN or automation_token in saved tokens (recommended)
      2. MULTILOGIN_TOKEN / saved token
      3. MULTILOGIN_EMAIL + MULTILOGIN_PASSWORD (signin)
      4. Refresh via saved refresh_token
    """

    def __init__(
        self,
        *,
        api_base: str = API_BASE,
        launcher_base: str = LAUNCHER_BASE,
        token: str | None = None,
        token_path: Path = TOKEN_PATH,
    ):
        self.api_base = api_base.rstrip("/")
        self.launcher_base = launcher_base.rstrip("/")
        self.token_path = token_path
        self._token = token
        self._refresh_token: str | None = None
        self._load_saved_tokens()

    def _load_saved_tokens(self) -> None:
        data: dict[str, Any] = {}
        if self.token_path.exists():
            data = yaml.safe_load(self.token_path.read_text(encoding="utf-8")) or {}
        if not self._token:
            # Prefer session token over automation_token — stale automation breaks post-signin.
            self._token = (
                os.getenv("MULTILOGIN_TOKEN")
                or data.get("token")
                or os.getenv("MULTILOGIN_AUTOMATION_TOKEN")
                or data.get("automation_token")
            )
        if not self._refresh_token:
            self._refresh_token = data.get("refresh_token")
        saved_email = data.get("email")
        if saved_email and not os.getenv("MULTILOGIN_EMAIL"):
            os.environ.setdefault("MULTILOGIN_EMAIL", str(saved_email))

    def save_tokens(
        self,
        *,
        token: str | None = None,
        refresh_token: str | None = None,
        automation_token: str | None = None,
        email: str | None = None,
    ) -> None:
        existing = {}
        if self.token_path.exists():
            existing = yaml.safe_load(self.token_path.read_text(encoding="utf-8")) or {}
        if token:
            existing["token"] = token
            existing.pop("automation_token", None)
            self._token = token
        if refresh_token:
            existing["refresh_token"] = refresh_token
            self._refresh_token = refresh_token
        if automation_token:
            existing["automation_token"] = automation_token
            self._token = automation_token
        if email:
            existing["email"] = email.strip()
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(yaml.safe_dump(existing, sort_keys=False), encoding="utf-8")

    def _saved_access_token(self) -> str | None:
        """Session access token for refresh (prefer token over automation_token)."""
        if self.token_path.exists():
            data = yaml.safe_load(self.token_path.read_text(encoding="utf-8")) or {}
            return data.get("token") or data.get("automation_token")
        return None

    def _drop_automation_token(self) -> None:
        """Remove expired automation token so signin/refresh session token is used."""
        if not self.token_path.exists():
            return
        data = yaml.safe_load(self.token_path.read_text(encoding="utf-8")) or {}
        if not data.pop("automation_token", None):
            return
        self.token_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        session = data.get("token")
        if session:
            self._token = session

    def _using_stale_automation_token(self) -> bool:
        if not self.token_path.exists():
            return False
        data = yaml.safe_load(self.token_path.read_text(encoding="utf-8")) or {}
        auto = data.get("automation_token")
        return bool(auto and self._token == auto)

    def _headers(self, *, launcher: bool = False, token: str | None = None) -> dict[str, str]:
        access = token or self.ensure_token()
        h = {"Accept": "application/json", "Authorization": f"Bearer {access}"}
        if not launcher:
            h["Content-Type"] = "application/json"
        return h

    def _refresh_request_headers(self) -> dict[str, str]:
        """MLX refresh_token expects Authorization with the current (possibly expired) access token."""
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        bearer = (
            self._token
            or os.getenv("MULTILOGIN_TOKEN")
            or self._saved_access_token()
        )
        if bearer:
            h["Authorization"] = f"Bearer {bearer}"
        return h

    def ensure_token(self) -> str:
        if self._token:
            return self._token
        email = os.getenv("MULTILOGIN_EMAIL")
        password = os.getenv("MULTILOGIN_PASSWORD")
        if email and password:
            return self.signin(email, password)
        if self._refresh_token:
            return self.refresh(self._refresh_token)
        raise MultiloginXError(
            "No Multilogin token. Set MULTILOGIN_AUTOMATION_TOKEN, MULTILOGIN_TOKEN, "
            "or MULTILOGIN_EMAIL + MULTILOGIN_PASSWORD, or run: nextbrowser multilogin signin"
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        launcher: bool = False,
        auth: bool = True,
        retries: int = 2,
        **kwargs,
    ) -> dict[str, Any]:
        extra_headers = kwargs.pop("headers", {}) or {}
        last_err = None
        for attempt in range(retries + 1):
            if auth:
                headers = self._headers(launcher=launcher)
            else:
                headers = {"Accept": "application/json", "Content-Type": "application/json"}
            headers.update(extra_headers)
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=kwargs.pop("timeout", 90),
                    **kwargs,
                )
            except requests.RequestException as e:
                last_err = MultiloginXError(str(e))
                time.sleep(1)
                continue
            if resp.status_code == 401 and attempt < retries:
                if self._using_stale_automation_token():
                    self._drop_automation_token()
                    self._load_saved_tokens()
                    continue
                if self._refresh_token:
                    self.refresh(self._refresh_token)
                    continue
            if not resp.ok:
                detail = _parse_api_error(resp)
                hint = ""
                if resp.status_code == 400 and "incorrect" in detail.lower():
                    hint = (
                        " Check MULTILOGIN_EMAIL / MULTILOGIN_PASSWORD (MLX account; password is "
                        "MD5-hashed on signin per Multilogin docs). Or set MULTILOGIN_AUTOMATION_TOKEN."
                    )
                elif resp.status_code == 401:
                    hint = " Token expired — run: nextbrowser multilogin signin"
                raise MultiloginXError(f"{method} {url} -> {resp.status_code}: {detail}.{hint}")
            if not resp.text:
                return {}
            return resp.json()
        raise last_err or MultiloginXError("request failed")

    def signin(self, email: str, password: str) -> str:
        email = (email or "").strip()
        password = (password or "").strip()
        if not email or not password:
            raise MultiloginXError("Email and password are required for signin.")
        data = self._request(
            "POST",
            f"{self.api_base}/user/signin",
            json={"email": email, "password": _signin_password(password)},
            auth=False,
        )
        block = data.get("data") or {}
        token = block.get("token")
        if not token:
            raise MultiloginXError(f"signin failed: {data}")
        self.save_tokens(token=token, refresh_token=block.get("refresh_token"), email=email)
        return token

    def refresh(self, refresh_token: str | None = None, *, email: str | None = None) -> str:
        rt = refresh_token or self._refresh_token
        if not rt:
            raise MultiloginXError("No refresh_token available")
        body: dict[str, str] = {"refresh_token": rt}
        em = (email or os.getenv("MULTILOGIN_EMAIL") or "").strip()
        if not em and self.token_path.exists():
            data_file = yaml.safe_load(self.token_path.read_text(encoding="utf-8")) or {}
            em = (data_file.get("email") or "").strip()
        if em:
            body["email"] = em
        data = self._request(
            "POST",
            f"{self.api_base}/user/refresh_token",
            json=body,
            auth=False,
            headers=self._refresh_request_headers(),
        )
        block = data.get("data") or {}
        token = block.get("token")
        if not token:
            raise MultiloginXError(f"refresh failed: {data}")
        self.save_tokens(token=token, refresh_token=block.get("refresh_token", rt))
        return token

    def fetch_automation_token(self, *, expiration_period: str | None = None) -> str:
        """
        GET /workspace/automation_token — longer-lived token for automation.

        Requires query param expiration_period (e.g. 1h, 24h, 1w per MLX docs).
        Override with MULTILOGIN_AUTOMATION_TOKEN_EXPIRY or pass expiration_period=.
        """
        if expiration_period is None:
            expiration_period = os.getenv("MULTILOGIN_AUTOMATION_TOKEN_EXPIRY", "24h")
        data = self._request(
            "GET",
            f"{self.api_base}/workspace/automation_token",
            params={"expiration_period": str(expiration_period)},
        )
        block = data.get("data") or {}
        token = block.get("automation_token") or block.get("token")
        if not token:
            raise MultiloginXError(f"automation_token missing: {data}")
        self.save_tokens(automation_token=token)
        return token

    def list_folders(self) -> list[dict]:
        data = self._request("GET", f"{self.api_base}/workspace/folders")
        return (data.get("data") or {}).get("folders") or []

    def create_profile(
        self,
        name: str,
        folder_id: str,
        *,
        browser_type: str = "mimic",
        os_type: str | None = None,
    ) -> str:
        """
        POST /profile/create — returns new profile UUID.
        Cookies/storage persist in MLX so a one-time login can be reused.
        """
        import platform as plat

        if not os_type:
            os_type = {
                "Windows": "windows",
                "Darwin": "macos",
                "Linux": "linux",
            }.get(plat.system(), "windows")
        body = {
            "name": name,
            "folder_id": folder_id,
            "browser_type": browser_type,
            "os_type": os_type,
            "parameters": {
                "flags": {
                    "audio_masking": "mask",
                    "fonts_masking": "natural",
                    "geolocation_masking": "mask",
                    "geolocation_popup": "prompt",
                    "graphics_masking": "mask",
                    "graphics_noise": "mask",
                    "localization_masking": "mask",
                    "media_devices_masking": "natural",
                    "navigator_masking": "mask",
                    "ports_masking": "mask",
                    "proxy_masking": "disabled",
                    "screen_masking": "mask",
                    "timezone_masking": "mask",
                    "webrtc_masking": "mask",
                },
                "storage": {
                    "bookmarks": True,
                    "cookies": True,
                    "extensions": True,
                    "history": True,
                    "local_storage": True,
                    "passwords": True,
                },
            },
        }
        data = self._request("POST", f"{self.api_base}/profile/create", json=body)
        block = data.get("data") or data
        profile_id = block.get("id") or block.get("profile_id") or block.get("uuid")
        if not profile_id:
            raise MultiloginXError(f"profile/create did not return id: {data}")
        return str(profile_id)

    def search_profiles(
        self,
        *,
        folder_id: str | None = None,
        search_text: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """POST /profile/search — search_text is required by API (empty string OK)."""
        body: dict[str, object] = {
            "search_text": search_text,
            "limit": limit,
            "offset": 0,
        }
        if folder_id:
            body["folder_id"] = folder_id
        data = self._request("POST", f"{self.api_base}/profile/search", json=body)
        return (data.get("data") or {}).get("profiles") or []

    def profile_active(self, profile_id: str) -> StartedProfile | None:
        """GET launcher /api/v1/profile/active — port if profile already running."""
        try:
            data = self._request(
                "GET",
                f"{self.launcher_base}/api/v1/profile/active",
                launcher=True,
                params={"profile_id": profile_id},
            )
        except MultiloginXError:
            return None
        block = data.get("data") or {}
        if block.get("is_active") and block.get("port"):
            return StartedProfile(
                profile_id=profile_id,
                folder_id=block.get("folder_id") or "",
                port=str(block.get("port")),
                browser_type=block.get("browser_type"),
                raw=data,
            )
        return None

    def profile_running(
        self, profile_id: str, *, folder_id: str = ""
    ) -> StartedProfile | None:
        """CDP port for an already-running profile (active endpoint, then status)."""
        active = self.profile_active(profile_id)
        if active and active.port:
            return active
        try:
            data = self.profile_status(profile_id)
        except MultiloginXError:
            return None
        block = data.get("data") or {}
        status = (block.get("status") or "").lower()
        port = block.get("port")
        if not port and status == "browser_running":
            port = block.get("message")
        if status == "browser_running" and port:
            return StartedProfile(
                profile_id=profile_id,
                folder_id=block.get("folder_id") or folder_id,
                port=str(port),
                browser_type=block.get("browser_type"),
                raw=data,
            )
        return None

    def stop_all_profiles(self) -> dict:
        return self._request(
            "GET",
            f"{self.launcher_base}/api/v1/profile/stop_all",
            launcher=True,
        )

    def start_profile(
        self,
        folder_id: str,
        profile_id: str,
        *,
        automation_type: str = "playwright",
        headless: bool = False,
        strict_mode: bool = False,
    ) -> StartedProfile:
        """
        GET /api/v2/profile/f/{folder_id}/p/{profile_id}/start
        Requires Multilogin X agent/launcher running locally.
        """
        params = {
            "automation_type": automation_type,
            "headless_mode": str(headless).lower(),
        }
        headers = self._headers(launcher=True)
        if strict_mode:
            headers["X-Strict-Mode"] = "true"
        try:
            data = self._request(
                "GET",
                f"{self.launcher_base}/api/v2/profile/f/{folder_id}/p/{profile_id}/start",
                launcher=True,
                params=params,
                headers=headers,
            )
        except MultiloginXError as e:
            err = str(e).lower()
            if (
                "already running" in err
                or "profile_already_running" in err
                or "browser process is running" in err
            ):
                active = self.profile_running(profile_id, folder_id=folder_id)
                if active and active.port:
                    return active
            raise
        block = data.get("data") or {}
        return StartedProfile(
            profile_id=profile_id,
            folder_id=folder_id,
            port=block.get("port"),
            browser_type=block.get("browser_type"),
            raw=data,
        )

    def stop_profile(self, profile_id: str) -> dict:
        try:
            return self._request(
                "GET",
                f"{self.launcher_base}/api/v1/profile/stop",
                launcher=True,
                params={"profile_id": profile_id},
            )
        except MultiloginXError as e:
            if "404" in str(e):
                return self.stop_all_profiles()
            raise

    def profile_status(self, profile_id: str) -> dict:
        return self._request(
            "GET",
            f"{self.launcher_base}/api/v1/profile/status/p/{profile_id}",
            launcher=True,
        )
