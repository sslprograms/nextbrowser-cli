from __future__ import annotations

from nextbrowser_harness.accounts.registry import AccountRegistry, SavedAccount
from nextbrowser_harness.config import HarnessConfig
from nextbrowser_harness.workflows.exec import exec_site


class AccountAutomationWorkflow:
    """Named Multilogin accounts — tier-3 exec over CDP with persistent MLX profiles."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.registry = AccountRegistry(config)

    def register_account(
        self,
        account_id: str,
        *,
        notes: str = "",
        display_name: str = "",
        mlx_profile_id: str = "",
        site: str = "",
        create_mlx: bool = False,
    ) -> SavedAccount:
        return self.registry.register(
            account_id,
            display_name=display_name or account_id,
            mlx_profile_id=mlx_profile_id,
            site=site,
            notes=notes,
            create_mlx=create_mlx,
        )

    def list_accounts(self) -> list[SavedAccount]:
        return self.registry.list_accounts()

    def run_account_task(
        self,
        account_id: str,
        task: str,
        *,
        url: str | None = None,
        tier: int | None = 3,
    ) -> dict:
        target_url = url or "https://example.com"
        actions = [task] if not task.startswith(("goto", "state", "click", "type", "eval", "find")) else [task]
        if not any(a.startswith("goto") for a in actions):
            actions = ["goto", *actions]
        result = exec_site(
            self.config,
            target_url,
            tier=tier or 3,
            profile_id=account_id,
            actions=actions,
        )
        out = result.to_dict()
        out["account_id"] = account_id
        return out
