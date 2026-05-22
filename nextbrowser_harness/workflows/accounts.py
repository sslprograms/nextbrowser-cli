from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.layers.automation.browser_use_adapter import BrowserUseLayer
from nextbrowser_harness.layers.automation.playwright_adapter import PlaywrightAutomationLayer
from nextbrowser_harness.layers.browser.antidetect import browser_layer_for
from nextbrowser_harness.layers.proxy import CustomProxyLayer, NodeMavenProxyLayer


@dataclass
class AccountProfile:
    account_id: str
    browser_profile: str
    proxy_session: str
    last_run: str | None = None
    notes: str = ""


class AccountAutomationWorkflow:
    """
    Persistent multi-account automation — isolated profile + sticky proxy per account.
    Sessions persist on disk; agent picks up where it left off.
    """

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.registry_path = Path(config.profiles_dir) / "accounts.json"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> dict[str, dict]:
        if not self.registry_path.exists():
            return {}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _save_registry(self, data: dict[str, dict]) -> None:
        self.registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def register_account(self, account_id: str, notes: str = "") -> AccountProfile:
        data = self._load_registry()
        profile = AccountProfile(
            account_id=account_id,
            browser_profile=f"acct_{account_id}",
            proxy_session=account_id,
            notes=notes,
        )
        data[account_id] = asdict(profile)
        self._save_registry(data)
        browser_layer_for(self.config).ensure_profile(profile.browser_profile)
        return profile

    def list_accounts(self) -> list[AccountProfile]:
        return [AccountProfile(**v) for v in self._load_registry().values()]

    def _automation(self):
        if self.config.automation == "browser_use":
            return BrowserUseLayer.from_config(self.config)
        return PlaywrightAutomationLayer.from_config(self.config)

    def _proxy_endpoint(self, session_id: str):
        if self.config.proxy == "nodemaven":
            return NodeMavenProxyLayer.from_config(self.config).get_endpoint(session_id)
        if self.config.custom_proxies:
            return CustomProxyLayer.from_config(self.config).get_endpoint(session_id)
        return None

    def run_account_task(self, account_id: str, task: str, *, url: str | None = None) -> dict:
        data = self._load_registry()
        if account_id not in data:
            self.register_account(account_id)
            data = self._load_registry()

        entry = data[account_id]
        entry["last_run"] = datetime.now(timezone.utc).isoformat()
        self._save_registry(data)

        # Each account: own profile path + sticky proxy session
        auto = self._automation()
        result = auto.run_task(task, url=url, profile_id=entry["browser_profile"])
        return {
            "account_id": account_id,
            "proxy_session": entry["proxy_session"],
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }
