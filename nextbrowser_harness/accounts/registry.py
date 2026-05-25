"""Persist named accounts → Multilogin profile UUIDs for tier-3 CDP automation."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nextbrowser_harness.config import HarnessConfig

_PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "user",
        "pass",
        "password",
        "username",
        "your_username",
        "your_password",
        "changeme",
        "xxx",
        "todo",
    }
)
_LOGIN_RECIPE_HINT = re.compile(r"(login|sign[_-]?in|auth|register)", re.I)


class Tier3AccountError(Exception):
    """Tier-3 exec blocked until the agent resolves account/credentials with the user."""

    def __init__(self, message: str, *, agent_prompt: str, code: str):
        super().__init__(message)
        self.agent_prompt = agent_prompt
        self.code = code


@dataclass
class SavedAccount:
    account_id: str
    display_name: str = ""
    mlx_profile_id: str = ""
    mlx_folder_id: str = ""
    site: str = ""
    notes: str = ""
    logged_in: bool = False
    created_at: str = ""
    last_run: str | None = None
    browser_profile: str = ""
    proxy_session: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AccountRegistry:
    """~/.nextbrowser/profiles/accounts.json + multilogin.profiles in config.yaml."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.registry_path = Path(config.profiles_dir) / "accounts.json"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict]:
        if not self.registry_path.exists():
            return {}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, dict]) -> None:
        self.registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_accounts(self) -> list[SavedAccount]:
        return [SavedAccount(**v) for v in self._load().values()]

    def get(self, account_id: str) -> SavedAccount | None:
        raw = self._load().get(account_id)
        if not raw:
            return None
        return SavedAccount(**raw)

    def _default_folder_id(self) -> str:
        mlx = self.config.multilogin or {}
        import os

        return str(mlx.get("folder_id") or os.getenv("MULTILOGIN_FOLDER_ID", "")).strip()

    def bind_mlx_profile(self, account_id: str, mlx_profile_id: str, *, folder_id: str = "") -> None:
        mlx = dict(self.config.multilogin or {})
        profiles = dict(mlx.get("profiles") or {})
        profiles[account_id] = mlx_profile_id
        mlx["profiles"] = profiles
        if folder_id:
            mlx["folder_id"] = folder_id
        self.config.multilogin = mlx
        self.config.save()

    def register(
        self,
        account_id: str,
        *,
        display_name: str = "",
        mlx_profile_id: str = "",
        mlx_folder_id: str = "",
        site: str = "",
        notes: str = "",
        create_mlx: bool = False,
    ) -> SavedAccount:
        folder_id = mlx_folder_id or self._default_folder_id()
        if create_mlx:
            if not folder_id:
                raise Tier3AccountError(
                    "MULTILOGIN_FOLDER_ID is not set. Run: nextbrowser multilogin setup-wizard",
                    agent_prompt=(
                        "MLX folder is missing. Ask the user to run "
                        "`nextbrowser multilogin setup-wizard`, then create the account again."
                    ),
                    code="mlx_folder_missing",
                )
            from nextbrowser_harness.integrations.multilogin.client import MultiloginXClient

            name = display_name or account_id.replace("_", " ").title()
            mlx_profile_id = MultiloginXClient().create_profile(name, folder_id)

        if not mlx_profile_id:
            raise Tier3AccountError(
                f"Account '{account_id}' needs a Multilogin profile. "
                "Use --create-mlx or --mlx-profile <uuid>.",
                agent_prompt=(
                    f"Ask the user: create a new Multilogin login for '{account_id}' "
                    f"(`nextbrowser account add {account_id} --create-mlx`), "
                    "or link an existing MLX profile UUID with --mlx-profile."
                ),
                code="mlx_profile_missing",
            )

        acc = SavedAccount(
            account_id=account_id,
            display_name=display_name or account_id,
            mlx_profile_id=mlx_profile_id,
            mlx_folder_id=folder_id,
            site=site,
            notes=notes,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        data = self._load()
        data[account_id] = acc.to_dict()
        self._save(data)
        self.bind_mlx_profile(account_id, mlx_profile_id, folder_id=folder_id)
        return acc

    def mark_logged_in(self, account_id: str, *, logged_in: bool = True) -> None:
        data = self._load()
        if account_id not in data:
            return
        data[account_id]["logged_in"] = logged_in
        data[account_id]["last_run"] = datetime.now(timezone.utc).isoformat()
        self._save(data)

    def touch_run(self, account_id: str) -> None:
        data = self._load()
        if account_id not in data:
            return
        data[account_id]["last_run"] = datetime.now(timezone.utc).isoformat()
        self._save(data)

    def resolve_mlx_profile(self, account_key: str) -> tuple[str, str]:
        """Return (folder_id, mlx_profile_uuid) for an account key."""
        acc = self.get(account_key)
        if acc and acc.mlx_profile_id:
            folder = acc.mlx_folder_id or self._default_folder_id()
            return folder, acc.mlx_profile_id
        mlx = self.config.multilogin or {}
        profiles = mlx.get("profiles") or {}
        pid = profiles.get(account_key) if isinstance(profiles, dict) else None
        if pid:
            return self._default_folder_id(), str(pid)
        return "", ""

    def require_for_tier3(self, account_key: str) -> SavedAccount:
        if not (account_key or "").strip():
            raise Tier3AccountError(
                "Tier 3 browser automation requires a named account (--account / --profile).",
                agent_prompt=(
                    "Ask the user: **Which saved account should I use?** "
                    "List options with `nextbrowser account list`. "
                    "Or ask: **Should I add a new login?** — if yes, get a name, "
                    "run `nextbrowser account add <name> --create-mlx`, then log in once "
                    "with exec + state/click/type and mark logged_in when done."
                ),
                code="account_required",
            )
        acc = self.get(account_key.strip())
        if not acc or not acc.mlx_profile_id:
            names = [a.account_id for a in self.list_accounts()]
            hint = f" Known accounts: {', '.join(names)}." if names else " No accounts yet — run account add."
            raise Tier3AccountError(
                f"No Multilogin-backed account '{account_key}'.{hint}",
                agent_prompt=(
                    f"Account '{account_key}' is not registered.{hint} "
                    "Ask: use an existing account, or create a new one with "
                    f"`nextbrowser account add <name> --create-mlx`?"
                ),
                code="account_unknown",
            )
        return acc

    def agent_summary(self) -> list[dict[str, Any]]:
        return [
            {
                "account_id": a.account_id,
                "display_name": a.display_name,
                "mlx_profile_id": a.mlx_profile_id,
                "site": a.site,
                "logged_in": a.logged_in,
                "last_run": a.last_run,
            }
            for a in self.list_accounts()
        ]
