"""Tier-3 automation must use Multilogin + a named account (CDP). Agents ask user when missing."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from nextbrowser_harness.accounts.registry import AccountRegistry, SavedAccount, Tier3AccountError
from nextbrowser_harness.config import HarnessConfig

_LOGIN_VAR_KEYS = frozenset(
    {"username", "password", "email", "pass", "user", "pwd", "login", "secret"}
)
_LOGIN_RECIPE_HINT = re.compile(r"(login|sign[_-]?in|auth|register)", re.I)
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


def _is_placeholder(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return True
    if v.upper() in ("USER", "PASS", "PASSWORD", "USERNAME", "YOUR_USERNAME", "YOUR_PASSWORD"):
        return True
    return v.lower() in _PLACEHOLDER_VALUES or v.startswith("$")


def action_needs_credentials(actions: list[str | dict] | None) -> bool:
    for raw in actions or []:
        text = raw if isinstance(raw, str) else str(raw.get("action") or raw.get("type") or "")
        if not text.startswith(("type:", "fill:")):
            continue
        if "|" not in text:
            continue
        _, val = text.split("|", 1)
        if _is_placeholder(val):
            return True
    return False


def recipe_needs_credentials(recipe: str | None, recipe_vars: dict[str, str] | None) -> bool:
    if recipe and _LOGIN_RECIPE_HINT.search(recipe):
        if not recipe_vars:
            return True
        for key in _LOGIN_VAR_KEYS:
            if key in {k.lower() for k in recipe_vars}:
                if _is_placeholder(str(recipe_vars.get(key) or recipe_vars.get(key.upper(), ""))):
                    return True
        if any(_is_placeholder(str(v)) for v in recipe_vars.values()):
            return True
    if recipe_vars:
        for k, v in recipe_vars.items():
            if k.lower() in _LOGIN_VAR_KEYS and _is_placeholder(str(v)):
                return True
    return False


def prepare_tier3_automation(
    config: HarnessConfig,
    *,
    resolved_tier: int,
    account_key: str,
    recipe: str | None = None,
    recipe_vars: dict[str, str] | None = None,
    actions: list[str | dict] | None = None,
) -> tuple[HarnessConfig, SavedAccount | None, dict[str, Any]]:
    """
    When resolved_tier is 3: force multilogin browser, require registered account, check credentials.
    Returns (config_copy, account, metadata) — metadata includes connection=cdp for agents.
    """
    if resolved_tier < 3:
        return config, None, {}

    registry = AccountRegistry(config)
    account = registry.require_for_tier3(account_key)

    if recipe_needs_credentials(recipe, recipe_vars) or action_needs_credentials(actions):
        raise Tier3AccountError(
            "Login credentials missing or placeholders for tier-3 automation.",
            agent_prompt=(
                "You do not have real credentials for this login. "
                "**Ask the user** for username/email and password (never guess). "
                "Then run exec with --recipe ... --var username=... --var password=... "
                "or --action \"type:N|value\" using indices from `state`."
            ),
            code="credentials_required",
        )

    cfg = deepcopy(config)
    cfg.browser = "multilogin"  # type: ignore[assignment]
    cfg.use_case = "accounts"  # type: ignore[assignment]

    meta = {
        "tier3_required": True,
        "connection": "cdp",
        "browser": "multilogin",
        "account_id": account.account_id,
        "mlx_profile_id": account.mlx_profile_id,
        "logged_in": account.logged_in,
    }
    return cfg, account, meta
